#requires -Version 5.1
<#
.SYNOPSIS
    ComplyForge Phase 10 demo launcher.

.DESCRIPTION
    Boots the four ComplyForge services in dependency order, waits for
    each to become healthy, seeds the inventory, and opens the dashboard.

      1. Backend FastAPI         (uvicorn main:app, port 8000)
      2. Veea Lobster Trap proxy (bin\lobstertrap.exe serve, port 8080)
      3. Webhook bridge          (lobstertrap\webhook_bridge.py)
      4. Frontend Vite dev       (npm run dev, port 5173)

    All four run as background jobs of THIS PowerShell session so Ctrl+C
    (or pressing 'q') tears every child process down. No supervisord, no
    pm2 — pure PowerShell + Python.

    Press 1-8 in this window to fire an attack payload, or invoke
    ./demo/fire_attack.ps1 -Index N from another shell.
#>

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
$Repo        = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Backend     = Join-Path $Repo 'backend'
$Lobstertrap = Join-Path $Repo 'lobstertrap'
$Frontend    = Join-Path $Repo 'frontend'
$VenvPython  = Join-Path $Backend '.venv\Scripts\python.exe'
$LobsterBin  = Join-Path $Lobstertrap 'bin\lobstertrap.exe'
$EnvFile     = Join-Path $Backend '.env'

function Step($msg)  { Write-Host "[demo] $msg" -ForegroundColor Cyan }
function Ok($msg)    { Write-Host "[ ok ] $msg" -ForegroundColor Green }
function Warn($msg)  { Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Fail($msg)  { Write-Host "[fail] $msg" -ForegroundColor Red ; exit 1 }

# ---------------------------------------------------------------------------
# Prereqs
# ---------------------------------------------------------------------------
Step 'Checking prerequisites'

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Fail "Backend venv missing at $VenvPython. Run: cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
}
if (-not (Test-Path -LiteralPath $LobsterBin)) {
    Fail "Lobster Trap binary missing at $LobsterBin. Run: cd lobstertrap; .\setup.ps1"
}
if (-not (Test-Path -LiteralPath (Join-Path $Frontend 'node_modules'))) {
    Fail "Frontend node_modules missing. Run: cd frontend; npm install"
}
if (-not (Test-Path -LiteralPath $EnvFile)) {
    Fail "Missing $EnvFile (need GEMINI_API_KEY=... ). See backend\.env.example."
}

# Parse .env without printing the secret.
$envHasKey = $false
foreach ($line in (Get-Content -LiteralPath $EnvFile)) {
    if ($line -match '^\s*GEMINI_API_KEY\s*=\s*(\S+)') {
        $envHasKey = -not [string]::IsNullOrWhiteSpace($Matches[1])
        break
    }
}
if (-not $envHasKey) {
    Fail "GEMINI_API_KEY is empty in $EnvFile. Real Gemini calls will fail."
}
Ok 'venv, binary, node_modules, GEMINI_API_KEY present'

# ---------------------------------------------------------------------------
# Background jobs
# ---------------------------------------------------------------------------
$jobs = @()

function Start-Service($name, $script, $args) {
    $job = Start-Job -Name $name -ScriptBlock {
        param($exe, $exeArgs, $cwd, $extraEnv)
        Set-Location -LiteralPath $cwd
        foreach ($k in $extraEnv.Keys) {
            Set-Item -Path "env:$k" -Value $extraEnv[$k]
        }
        & $exe @exeArgs 2>&1
    } -ArgumentList $script.Exe, $script.Args, $script.Cwd, $script.Env
    $script:jobs += [pscustomobject]@{ Name = $name; Job = $job }
    return $job
}

# 1. Backend
$backendJob = Start-Service 'backend' @{
    Exe  = $VenvPython
    Args = @('-m', 'uvicorn', 'main:app', '--port', '8000', '--log-level', 'info')
    Cwd  = $Backend
    Env  = @{}
}

# 2. Lobster Trap
$lobsterJob = Start-Service 'lobstertrap' @{
    Exe  = $LobsterBin
    Args = @(
        'serve',
        '--policy', 'policies\default.yaml',
        '--backend', 'https://generativelanguage.googleapis.com',
        '--listen', ':8080'
    )
    Cwd  = $Lobstertrap
    Env  = @{}
}

# 3. Webhook bridge (uses the backend venv's python)
$bridgeJob = Start-Service 'bridge' @{
    Exe  = $VenvPython
    Args = @('webhook_bridge.py')
    Cwd  = $Lobstertrap
    Env  = @{
        COMPLYFORGE_URL          = 'http://localhost:8000'
        LOBSTERTRAP_EVENT_SOURCE = 'http://localhost:8080'
    }
}

# 4. Frontend
$frontendJob = Start-Service 'frontend' @{
    Exe  = 'npm.cmd'
    Args = @('run', 'dev')
    Cwd  = $Frontend
    Env  = @{}
}

# ---------------------------------------------------------------------------
# Cleanup wiring (handles Ctrl+C and `q`)
# ---------------------------------------------------------------------------
function Stop-Demo {
    Step 'Stopping demo services'
    foreach ($entry in $script:jobs) {
        try {
            Stop-Job -Job $entry.Job -ErrorAction SilentlyContinue
            Remove-Job -Job $entry.Job -Force -ErrorAction SilentlyContinue
            Ok ("stopped {0}" -f $entry.Name)
        } catch {
            Warn ("failed to stop {0}: {1}" -f $entry.Name, $_)
        }
    }
}

Register-EngineEvent PowerShell.Exiting -Action { Stop-Demo } | Out-Null
[Console]::TreatControlCAsInput = $true

# ---------------------------------------------------------------------------
# Health probes
# ---------------------------------------------------------------------------
function Test-Endpoint($url, $timeoutSec = 30) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 400
        }
    }
    return $false
}

Step 'Waiting for backend on :8000'
if (-not (Test-Endpoint 'http://localhost:8000/' 30)) {
    Stop-Demo
    Fail 'Backend did not become healthy within 30s.'
}
Ok 'backend healthy'

Step 'Waiting for Lobster Trap on :8080'
if (-not (Test-Endpoint 'http://localhost:8080/_lobstertrap/api/policy' 30)) {
    Stop-Demo
    Fail 'Lobster Trap did not become healthy within 30s.'
}
Ok 'lobstertrap healthy'

Step 'Checking webhook bridge process'
if ($bridgeJob.State -eq 'Failed' -or $bridgeJob.State -eq 'Stopped') {
    Stop-Demo
    Fail "Webhook bridge job state is $($bridgeJob.State). See: Receive-Job -Name bridge"
}
Ok 'bridge running'

Step 'Waiting for frontend on :5173'
if (-not (Test-Endpoint 'http://localhost:5173/' 30)) {
    Stop-Demo
    Fail 'Frontend did not become healthy within 30s.'
}
Ok 'frontend healthy'

# ---------------------------------------------------------------------------
# Seed the inventory
# ---------------------------------------------------------------------------
Step 'Seeding inventory (5 sample agents -> POST /api/analyze)'
try {
    & $VenvPython (Join-Path $Backend 'scripts\seed_inventory.py')
    if ($LASTEXITCODE -ne 0) {
        Warn "seed_inventory.py exited with code $LASTEXITCODE; dashboard may be empty"
    } else {
        Ok 'inventory seeded'
    }
} catch {
    Warn ("seed_inventory failed: {0}" -f $_.Exception.Message)
}

# ---------------------------------------------------------------------------
# Open browser + interactive loop
# ---------------------------------------------------------------------------
Step 'Opening http://localhost:5173 in default browser'
Start-Process 'http://localhost:5173'

Write-Host ''
Write-Host '=========================================================' -ForegroundColor DarkGray
Write-Host ' ComplyForge demo is live' -ForegroundColor Green
Write-Host '=========================================================' -ForegroundColor DarkGray
Write-Host '  Dashboard          : http://localhost:5173' -ForegroundColor Gray
Write-Host '  Backend API        : http://localhost:8000' -ForegroundColor Gray
Write-Host '  Lobster Trap proxy : http://localhost:8080' -ForegroundColor Gray
Write-Host '  Lobster Trap admin : http://localhost:8080/_lobstertrap/' -ForegroundColor Gray
Write-Host ''
Write-Host '  Press 1-8 to fire the matching attack payload' -ForegroundColor Yellow
Write-Host '  Or run    .\demo\fire_attack.ps1 -Index N    in another shell' -ForegroundColor Yellow
Write-Host '  Press q   to stop all services' -ForegroundColor Yellow
Write-Host ''

$fireScript = Join-Path $PSScriptRoot 'fire_attack.ps1'

while ($true) {
    if ([Console]::KeyAvailable) {
        $key = [Console]::ReadKey($true)
        $ch = $key.KeyChar
        # Ctrl+C also lands here because TreatControlCAsInput=true.
        if (($key.Modifiers -band [ConsoleModifiers]::Control) -and ($key.Key -eq [ConsoleKey]::C)) {
            break
        }
        if ($ch -eq 'q' -or $ch -eq 'Q') { break }
        if ($ch -ge '1' -and $ch -le '8') {
            $idx = [int]::Parse([string]$ch)
            Step "Firing attack payload #$idx"
            try {
                & $fireScript -Index $idx
            } catch {
                Warn ("fire_attack failed: {0}" -f $_.Exception.Message)
            }
        }
    } else {
        Start-Sleep -Milliseconds 150
    }

    # Surface unexpected job exits early.
    foreach ($entry in $jobs) {
        if ($entry.Job.State -eq 'Failed' -or $entry.Job.State -eq 'Completed') {
            Warn ("service {0} stopped (state={1})" -f $entry.Name, $entry.Job.State)
            Receive-Job -Job $entry.Job -ErrorAction SilentlyContinue | Select-Object -Last 5 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        }
    }
}

Stop-Demo
Write-Host '[ ok ] all services stopped' -ForegroundColor Green
