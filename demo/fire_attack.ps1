#requires -Version 5.1
<#
.SYNOPSIS
    Fire one of the 8 ComplyForge attack payloads at the Lobster Trap proxy
    and show the relayed enforcement event from the ComplyForge backend.

.PARAMETER Index
    1-based index into backend/app/data/attack_payloads.json (1..8).

.PARAMETER ProxyUrl
    Base URL of the Lobster Trap proxy. Defaults to http://localhost:8080.

.PARAMETER BackendUrl
    Base URL of the ComplyForge backend. Defaults to http://localhost:8000.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 8)]
    [int]$Index,

    [string]$ProxyUrl   = 'http://localhost:8080',
    [string]$BackendUrl = 'http://localhost:8000'
)

$ErrorActionPreference = 'Stop'

$Repo         = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PayloadsPath = Join-Path $Repo 'backend\app\data\attack_payloads.json'

if (-not (Test-Path -LiteralPath $PayloadsPath)) {
    Write-Host "[fail] attack_payloads.json missing at $PayloadsPath" -ForegroundColor Red
    exit 1
}

$payloads = Get-Content -LiteralPath $PayloadsPath -Raw | ConvertFrom-Json
if ($Index -lt 1 -or $Index -gt $payloads.Count) {
    Write-Host "[fail] Index $Index out of range (have $($payloads.Count) payloads)" -ForegroundColor Red
    exit 1
}

$attack = $payloads[$Index - 1]

Write-Host '' 
Write-Host '=========================================================' -ForegroundColor DarkGray
Write-Host (" Attack #{0}: {1}" -f $Index, $attack.name) -ForegroundColor Yellow
Write-Host (" Expected   : action={0}  rule={1}  article={2}" -f $attack.expected_action, $attack.expected_rule, $attack.eu_ai_act_article) -ForegroundColor Gray
Write-Host (" Narrative  : {0}" -f $attack.narrative) -ForegroundColor Gray
Write-Host '=========================================================' -ForegroundColor DarkGray
Write-Host ''

# Build an OpenAI-compatible chat completion body. Lobster Trap inspects the
# user message before forwarding to the configured backend.
$chatBody = @{
    model    = 'gemini-2.0-flash-exp'
    messages = @(
        @{ role = 'user'; content = $attack.payload }
    )
} | ConvertTo-Json -Depth 4

$proxyEndpoint = "{0}/v1/chat/completions" -f $ProxyUrl.TrimEnd('/')

Write-Host "[fire] POST $proxyEndpoint" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest -Uri $proxyEndpoint `
        -Method Post `
        -Body $chatBody `
        -ContentType 'application/json' `
        -UseBasicParsing `
        -TimeoutSec 15 `
        -ErrorAction Stop
    Write-Host ("[resp] status={0}  body={1}" -f $resp.StatusCode, ($resp.Content -replace '\s+', ' ').Substring(0, [Math]::Min(280, $resp.Content.Length))) -ForegroundColor Gray
} catch {
    $err = $_.Exception
    if ($err.Response) {
        $status = [int]$err.Response.StatusCode
        $stream = $err.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $body   = $reader.ReadToEnd()
        Write-Host ("[deny] status={0}  body={1}" -f $status, ($body -replace '\s+', ' ').Substring(0, [Math]::Min(280, $body.Length))) -ForegroundColor Magenta
    } else {
        Write-Host ("[err ] {0}" -f $err.Message) -ForegroundColor Red
    }
}

Start-Sleep -Seconds 2

$eventsEndpoint = "{0}/api/enforcement/events?limit=5" -f $BackendUrl.TrimEnd('/')
Write-Host '' 
Write-Host "[poll] GET $eventsEndpoint" -ForegroundColor Cyan
try {
    $events = Invoke-RestMethod -Uri $eventsEndpoint -TimeoutSec 5
} catch {
    Write-Host ("[err ] events endpoint not reachable: {0}" -f $_.Exception.Message) -ForegroundColor Red
    exit 1
}

if (-not $events -or $events.Count -eq 0) {
    Write-Host '[empty] no enforcement events yet (webhook bridge may still be relaying — try again in a second)' -ForegroundColor Yellow
} else {
    $latest = $events[0]
    Write-Host '[event] latest enforcement event:' -ForegroundColor Green
    Write-Host ("  timestamp : {0}" -f $latest.timestamp) -ForegroundColor Gray
    Write-Host ("  action    : {0}" -f $latest.action) -ForegroundColor Gray
    Write-Host ("  rule      : {0}" -f $latest.rule_triggered) -ForegroundColor Gray
    Write-Host ("  agent     : {0}" -f $latest.agent_name) -ForegroundColor Gray
    if ($latest.rule_triggered -eq $attack.expected_rule) {
        Write-Host '[match] rule_triggered matches expected_rule' -ForegroundColor Green
    } else {
        Write-Host ('[diff ] expected rule "{0}" but got "{1}"' -f $attack.expected_rule, $latest.rule_triggered) -ForegroundColor Yellow
    }
}
