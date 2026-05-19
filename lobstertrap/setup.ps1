#requires -Version 5.1
<#
.SYNOPSIS
    ComplyForge the build step setup: clone Veea Lobster Trap, build the binary, verify.

.DESCRIPTION
    Clones github.com/veeainc/lobstertrap into ./src (if missing), reads its
    real layout, and builds bin\lobstertrap.exe. Fails loud with actionable
    next steps if git or go are missing — never silently fakes a binary.

    Schema and CLI flags inspected by the build step are recorded in
    ./SCHEMA_NOTES.md.
#>

$ErrorActionPreference = 'Stop'

$Root      = Split-Path -Parent $PSCommandPath
$SrcDir    = Join-Path $Root 'src'
$BinDir    = Join-Path $Root 'bin'
$Binary    = Join-Path $BinDir 'lobstertrap.exe'
$RepoUrl   = 'https://github.com/veeainc/lobstertrap.git'  # canonical Veea fork
$MirrorUrl = 'https://github.com/coal/lobstertrap.git'      # original author

function Step($msg) { Write-Host "[setup] $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "[ ok ] $msg" -ForegroundColor Green }
function Fail($msg) {
    Write-Host "[fail] $msg" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# 1. Tooling preflight
# ---------------------------------------------------------------------------
Step 'Checking git'
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Fail @'
git not found on PATH.
  Install Git for Windows from https://git-scm.com/download/win and re-run
  this script from a fresh PowerShell session.
'@
}
Ok ("git -> {0}" -f (& git --version))

Step 'Checking go'
$go = Get-Command go -ErrorAction SilentlyContinue
if (-not $go) {
    Fail @'
go not found on PATH.
  Install Go 1.22+ from https://go.dev/dl/ and re-run this script.
  Without Go we cannot build the Lobster Trap binary; ComplyForge will not
  fabricate a fake binary or silently fall back to a Python simulator.
'@
}
$goVersion = & go version
Ok ("go  -> {0}" -f $goVersion)

# ---------------------------------------------------------------------------
# 2. Clone Lobster Trap if missing
# ---------------------------------------------------------------------------
if (-not (Test-Path -LiteralPath $SrcDir)) {
    Step "Cloning Lobster Trap into $SrcDir"
    try {
        & git clone --depth=1 $RepoUrl $SrcDir
    } catch {
        Write-Host "[warn] clone of $RepoUrl failed; trying mirror $MirrorUrl" -ForegroundColor Yellow
        try {
            & git clone --depth=1 $MirrorUrl $SrcDir
        } catch {
            Fail @"
Could not clone Lobster Trap from either:
    $RepoUrl
    $MirrorUrl
Network unavailable or both repos unreachable from this machine.
Clone manually on a network where GitHub is reachable, drop the result at:
    $SrcDir
and re-run this script.
"@
        }
    }
    Ok 'clone complete'
} else {
    Ok "src/ already present at $SrcDir (skipping clone)"
}

# ---------------------------------------------------------------------------
# 3. Inspect the real package layout
# ---------------------------------------------------------------------------
$readme = Join-Path $SrcDir 'README.md'
$goMod  = Join-Path $SrcDir 'go.mod'
if (-not (Test-Path -LiteralPath $goMod)) {
    Fail "go.mod missing under $SrcDir; clone is incomplete or layout changed."
}
if (-not (Test-Path -LiteralPath $readme)) {
    Write-Host "[warn] README.md not found under $SrcDir; continuing with default build path." -ForegroundColor Yellow
}

# upstream inspection (verified during clone): the canonical entrypoint lives
# at src/main.go (`package main`); there is NO src/cmd/lobstertrap subpackage.
# Try the the architecture spec-suggested path first for forward-compat, then fall back
# to the real build target documented in the repo's Makefile.
$cmdMain = Join-Path $SrcDir 'cmd\lobstertrap'

if (-not (Test-Path -LiteralPath $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir | Out-Null
}

Step 'Building lobstertrap.exe'
Push-Location -LiteralPath $SrcDir
try {
    if (Test-Path -LiteralPath $cmdMain) {
        Step "Building from .\cmd\lobstertrap (forward-compat path)"
        & go build -o $Binary '.\cmd\lobstertrap'
    } else {
        Step 'Building from . (real Veea repo layout — main.go at root)'
        & go build -o $Binary '.'
    }
    if ($LASTEXITCODE -ne 0) {
        Fail "go build failed with exit code $LASTEXITCODE; see error above."
    }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $Binary)) {
    Fail "Build reported success but $Binary is missing; aborting."
}
Ok "binary -> $Binary"

# ---------------------------------------------------------------------------
# 4. Verify the binary
# ---------------------------------------------------------------------------
Step 'Verifying binary'
# Real CLI exposes both `version` (subcommand) and `--version` flag wiring via
# cobra. Try the subcommand first; fall back to the flag. Route through cmd.exe
# so PowerShell's $ErrorActionPreference='Stop' doesn't promote any stderr
# noise (which Go-based CLIs commonly emit) into a terminating error.
$versionOut = & cmd.exe /c "`"$Binary`" version 2>&1"
$versionExit = $LASTEXITCODE
if ($versionExit -ne 0 -or -not $versionOut) {
    $versionOut = & cmd.exe /c "`"$Binary`" --version 2>&1"
    $versionExit = $LASTEXITCODE
}
if ($versionExit -ne 0) {
    Fail "Binary built but neither ``version`` nor ``--version`` exited cleanly (exit=$versionExit, output=$versionOut)."
}
Ok ("version -> {0}" -f (($versionOut | Where-Object { $_ -match '\S' }) -join ' '))

# ---------------------------------------------------------------------------
# 5. Sanity-load the ComplyForge baseline policy (proves YAML compatibility)
# ---------------------------------------------------------------------------
$defaultPolicy = Join-Path $Root 'policies\default.yaml'
if (Test-Path -LiteralPath $defaultPolicy) {
    Step 'Loading policies/default.yaml through the real Lobster Trap loader'
    Push-Location -LiteralPath $Root
    try {
        # `inspect` runs policy.LoadFromFile + validate; any schema problem
        # surfaces here. Route through cmd.exe to ignore stderr noise and
        # only trust the exit code.
        & cmd.exe /c "`"$Binary`" inspect --policy `"$defaultPolicy`" hello 1>NUL 2>&1"
        if ($LASTEXITCODE -ne 0) {
            Fail "default.yaml failed to load (exit $LASTEXITCODE)."
        }
        Ok 'default.yaml validated by real Go loader'
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[warn] policies/default.yaml missing; skipping validation." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 6. Next steps
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '=========================================================' -ForegroundColor DarkGray
Write-Host ' Lobster Trap is built and ready.' -ForegroundColor Green
Write-Host '=========================================================' -ForegroundColor DarkGray
Write-Host ''
Write-Host '  Start the proxy in one terminal:'
Write-Host "    .\bin\lobstertrap.exe serve --policy policies\default.yaml --backend https://generativelanguage.googleapis.com --listen :8080"
Write-Host ''
Write-Host '  Start the ComplyForge backend in another (from backend/):'
Write-Host '    .\.venv\Scripts\Activate.ps1; uvicorn main:app --reload --port 8000'
Write-Host ''
Write-Host '  Start the webhook bridge in a third:'
Write-Host '    $env:COMPLYFORGE_URL = "http://localhost:8000"'
Write-Host '    $env:LOBSTERTRAP_EVENT_SOURCE = "http://localhost:8080"'
Write-Host '    .\..\backend\.venv\Scripts\python.exe webhook_bridge.py'
Write-Host ''
Write-Host '  Then send a malicious test prompt at http://localhost:8080 and'
Write-Host '  watch ComplyForge audit_logs/events.jsonl light up.'
Write-Host ''
