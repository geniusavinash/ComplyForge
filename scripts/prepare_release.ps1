#requires -Version 5.1
<#
.SYNOPSIS
    ComplyForge final preflight before lablab.ai submission.

.DESCRIPTION
    Runs the machine-checkable items from SUBMISSION_PACKAGE.md, surfaces
    every remaining placeholder with file:line, and refuses to claim
    success unless every check is green. The script never publishes,
    pushes to GitHub, or uploads anything; those are manual steps.
#>

$ErrorActionPreference = 'Stop'

$Repo        = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Backend     = Join-Path $Repo 'backend'
$Frontend    = Join-Path $Repo 'frontend'
$Lobstertrap = Join-Path $Repo 'lobstertrap'
$Demo        = Join-Path $Repo 'demo'
$Docs        = Join-Path $Repo 'docs'
$VenvPython  = Join-Path $Backend '.venv\Scripts\python.exe'
$LobsterBin  = Join-Path $Lobstertrap 'bin\lobstertrap.exe'
$EnvFile     = Join-Path $Backend '.env'

$script:GreenChecks = 0
$script:RedChecks   = 0

function Pass($msg) { Write-Host "[ ok ] $msg" -ForegroundColor Green ; $script:GreenChecks += 1 }
function Fail($msg) { Write-Host "[fail] $msg" -ForegroundColor Red   ; $script:RedChecks   += 1 }
function Warn($msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Step($msg) { Write-Host "[step] $msg" -ForegroundColor Cyan }

function Test-FileNonEmpty($path) {
    if (Test-Path -LiteralPath $path) {
        $size = (Get-Item -LiteralPath $path).Length
        return $size -gt 0
    }
    return $false
}

# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------
Step 'Environment'

if (Test-Path -LiteralPath $VenvPython) {
    Pass "backend venv at $VenvPython"
} else {
    Fail "backend venv missing at $VenvPython (run: cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt)"
}

if (Test-Path -LiteralPath $EnvFile) {
    $hasKey = $false
    foreach ($line in (Get-Content -LiteralPath $EnvFile)) {
        if ($line -match '^\s*GEMINI_API_KEY\s*=\s*(\S+)') {
            $hasKey = -not [string]::IsNullOrWhiteSpace($Matches[1])
            break
        }
    }
    if ($hasKey) {
        Pass "GEMINI_API_KEY present in backend\.env (value not printed)"
    } else {
        Fail "GEMINI_API_KEY missing or empty in $EnvFile"
    }
} else {
    Fail "backend\.env missing (copy backend\.env.example and paste your key)"
}

if (Test-Path -LiteralPath $LobsterBin) {
    Pass "Lobster Trap binary at $LobsterBin"
} else {
    Fail "Lobster Trap binary missing (run: cd lobstertrap; .\setup.ps1)"
}

if (Test-Path -LiteralPath (Join-Path $Frontend 'node_modules')) {
    Pass "frontend node_modules present"
} else {
    Fail "frontend node_modules missing (run: cd frontend; npm install)"
}

# ---------------------------------------------------------------------------
# Required files
# ---------------------------------------------------------------------------
Step 'Required files'

$requiredFiles = @(
    @{ Path = Join-Path $Repo 'README.md';                         Label = 'README.md' },
    @{ Path = Join-Path $Repo 'LICENSE';                           Label = 'LICENSE' },
    @{ Path = Join-Path $Repo 'CONTRIBUTING.md';                   Label = 'CONTRIBUTING.md' },
    @{ Path = Join-Path $Repo 'SUBMISSION_PACKAGE.md';             Label = 'SUBMISSION_PACKAGE.md' },
    @{ Path = Join-Path $Docs 'ARCHITECTURE.md';                   Label = 'docs\ARCHITECTURE.md' },
    @{ Path = Join-Path $Docs 'EU_AI_ACT_MAPPING.md';              Label = 'docs\EU_AI_ACT_MAPPING.md' },
    @{ Path = Join-Path $Repo '.github\workflows\test.yml';        Label = '.github\workflows\test.yml' },
    @{ Path = Join-Path $Demo 'pitch_deck.md';                     Label = 'demo\pitch_deck.md' },
    @{ Path = Join-Path $Demo 'script.md';                         Label = 'demo\script.md' },
    @{ Path = Join-Path $Demo 'attack_scenarios.md';               Label = 'demo\attack_scenarios.md' },
    @{ Path = Join-Path $Demo 'judge_qa.md';                       Label = 'demo\judge_qa.md' },
    @{ Path = Join-Path $Demo 'run_demo.ps1';                      Label = 'demo\run_demo.ps1' },
    @{ Path = Join-Path $Demo 'fire_attack.ps1';                   Label = 'demo\fire_attack.ps1' }
)

foreach ($f in $requiredFiles) {
    if (Test-FileNonEmpty $f.Path) {
        Pass ("{0} exists and is non-empty" -f $f.Label)
    } else {
        Fail ("{0} missing or empty" -f $f.Label)
    }
}

# ---------------------------------------------------------------------------
# Backend tests (unit only)
# ---------------------------------------------------------------------------
Step 'Backend pytest (unit)'

if (Test-Path -LiteralPath $VenvPython) {
    Push-Location -LiteralPath $Backend
    try {
        # Same stderr-tolerant pattern as the frontend build below: pytest's
        # warning summary lands on stderr and would otherwise trip
        # $ErrorActionPreference='Stop' through Tee-Object.
        $pyArgs = ('"{0}" -m pytest tests/ -v -m "not e2e" 2>&1' -f $VenvPython)
        $pytestOutput = cmd.exe /c $pyArgs
        $exit = $LASTEXITCODE
        $summaryLine = ($pytestOutput | Select-String -Pattern '\d+ passed' | Select-Object -Last 1)
        $summary = if ($summaryLine) { $summaryLine.ToString().Trim() } else { 'no summary line captured' }
        if ($exit -eq 0) {
            Pass ("pytest passed: {0}" -f $summary)
        } else {
            $tail = ($pytestOutput | Select-Object -Last 6) -join "`n"
            Fail ("pytest exited {0}; tail:`n{1}" -f $exit, $tail)
        }
    } finally {
        Pop-Location
    }
} else {
    Fail 'pytest skipped (venv missing)'
}

# ---------------------------------------------------------------------------
# Frontend build
# ---------------------------------------------------------------------------
Step 'Frontend build'

if (Test-Path -LiteralPath (Join-Path $Frontend 'node_modules')) {
    Push-Location -LiteralPath $Frontend
    try {
        # `npm run build` (Vite) writes the chunk-size advisory to stderr; we
        # redirect 2>&1 inside cmd.exe so PowerShell's Stop-on-stderr behaviour
        # doesn't promote the warning into a terminating error. Trust the
        # exit code, not stderr presence.
        $buildOutput = cmd.exe /c "npm.cmd run build 2>&1"
        $exit = $LASTEXITCODE
        if ($exit -eq 0) {
            $line = ($buildOutput | Select-String -Pattern 'built in' | Select-Object -Last 1)
            if ($line) { $line = $line.ToString().Trim() } else { $line = 'npm run build exit 0' }
            Pass ("frontend build OK ({0})" -f $line)
        } else {
            $tail = ($buildOutput | Select-Object -Last 6) -join "`n"
            Fail ("npm run build exited {0}; tail:`n{1}" -f $exit, $tail)
        }
    } finally {
        Pop-Location
    }
} else {
    Fail 'frontend build skipped (node_modules missing)'
}

# ---------------------------------------------------------------------------
# Seeded PDF inventory
# ---------------------------------------------------------------------------
Step 'Seeded PDF inventory'

$pdfDir = Join-Path $Backend 'generated_pdfs'
if (Test-Path -LiteralPath $pdfDir) {
    $pdfs = Get-ChildItem -LiteralPath $pdfDir -Filter *.pdf -File -ErrorAction SilentlyContinue
    if ($pdfs.Count -ge 5) {
        Pass ("{0} PDFs found in backend\generated_pdfs\" -f $pdfs.Count)
    } else {
        Fail ("only {0} PDFs in backend\generated_pdfs\ (expected >= 5; run scripts/seed_inventory.py against a live backend)" -f $pdfs.Count)
    }
} else {
    Fail "backend\generated_pdfs\ does not exist (run scripts/seed_inventory.py against a live backend)"
}

# ---------------------------------------------------------------------------
# Placeholder scan
# ---------------------------------------------------------------------------
Step 'Placeholder scan'

$placeholderPattern = '\{\{(GITHUB_USERNAME|LABLAB_TEAM_NAME|YOUTUBE_VIDEO_ID)\}\}'
$placeholderHits = Get-ChildItem -LiteralPath $Repo -Recurse -File `
    -Include *.md, *.ps1, *.yml, *.yaml, *.json, *.html `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $p = $_.FullName
        ($p -notmatch '\\\.venv\\') -and
        ($p -notmatch '\\node_modules\\') -and
        ($p -notmatch '\\dist\\') -and
        ($p -notmatch '\\\.git\\') -and
        ($p -notmatch '\\lobstertrap\\src\\') -and
        ($p -notmatch '\\lobstertrap\\bin\\') -and
        ($p -notmatch '\\backend\\generated_pdfs\\') -and
        ($p -notmatch '\\backend\\\.pytest_cache\\')
    } |
    Select-String -Pattern $placeholderPattern

if ($placeholderHits) {
    Warn ("{0} placeholder occurrences still present (these are EXPECTED until you publish; the human resolves them):" -f $placeholderHits.Count)
    foreach ($hit in $placeholderHits) {
        $rel = $hit.Path.Replace($Repo, '').TrimStart('\')
        Write-Host ("  {0}:{1}: {2}" -f $rel, $hit.LineNumber, $hit.Line.Trim()) -ForegroundColor DarkGray
    }
    Pass 'placeholders surfaced for manual replacement'
} else {
    Pass 'no remaining template placeholders'
}

# ---------------------------------------------------------------------------
# Forbidden token scan in pitch / video / scenarios / judge_qa
# ---------------------------------------------------------------------------
Step 'Forbidden token scan (cliches / emoji)'

$cliches = '\b(revolutionary|disruptive|game[- ]changer|next[- ]generation|AI[- ]powered|blazing[- ]fast)\b'
$cliFiles = @(
    (Join-Path $Demo 'pitch_deck.md'),
    (Join-Path $Demo 'script.md'),
    (Join-Path $Demo 'attack_scenarios.md'),
    (Join-Path $Demo 'judge_qa.md')
) | Where-Object { Test-Path -LiteralPath $_ }

$cliHits = $cliFiles | Select-String -Pattern $cliches -CaseSensitive:$false
if ($cliHits) {
    Fail "marketing cliches found in demo content:"
    foreach ($h in $cliHits) {
        $rel = $h.Path.Replace($Repo, '').TrimStart('\')
        Write-Host ("  {0}:{1}: {2}" -f $rel, $h.LineNumber, $h.Line.Trim()) -ForegroundColor Red
    }
} else {
    Pass 'no marketing cliches in pitch / video / scenarios / Q&A'
}

$emojiHit = $false
foreach ($file in $cliFiles) {
    $bytes = [System.IO.File]::ReadAllBytes($file)
    for ($i = 0; $i -lt $bytes.Length - 3; $i++) {
        if ($bytes[$i] -eq 0xF0 -and $bytes[$i + 1] -ge 0x9F -and $bytes[$i + 1] -le 0x9F) {
            $emojiHit = $true
            $rel = $file.Replace($Repo, '').TrimStart('\')
            Fail "emoji byte sequence found in $rel"
            break
        }
    }
    if ($emojiHit) { break }
}
if (-not $emojiHit) { Pass 'no emoji byte sequences in demo content' }

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
$summaryColor = if ($script:RedChecks -eq 0) { 'Green' } else { 'Red' }
Write-Host ''
Write-Host '=========================================================' -ForegroundColor DarkGray
Write-Host (' Preflight complete.  green={0}  red={1}' -f $script:GreenChecks, $script:RedChecks) -ForegroundColor $summaryColor
Write-Host '=========================================================' -ForegroundColor DarkGray

if ($script:RedChecks -eq 0) {
    Write-Host ' All machine-checkable items pass.  Remaining work is manual:' -ForegroundColor Green
    Write-Host '   1. Replace {{LABLAB_TEAM_NAME}} and {{YOUTUBE_VIDEO_ID}}'
    Write-Host '      placeholders in SUBMISSION_PACKAGE.md.'
    Write-Host '   2. Push the public GitHub repo and tag v0.1.0.'
    Write-Host '   3. Record + upload the demo video (YouTube unlisted).'
    Write-Host '   4. Paste team-page fields into lablab.ai.'
    Write-Host '   5. Submit before 2026-05-19.'
    exit 0
} else {
    Write-Host ' Some checks failed. Fix them, then re-run scripts\prepare_release.ps1.' -ForegroundColor Red
    exit 1
}
