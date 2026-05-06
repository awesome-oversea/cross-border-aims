<#
AIMS AI Marketing System - Host Gateway Foreground Runner
All paths locked to D: drive, no C: drive writes
#>

$ErrorActionPreference = "Stop"

$AIMS_HOME = "D:\Project\aims"
$PORTABLE_ROOT = "D:\openclaw\openclaw-portable-win-x64"
$ENV_PATH = Join-Path $AIMS_HOME ".env"
$OPENCLAW_HOME = Join-Path $AIMS_HOME ".generated\openclaw-host-home"
$HELPER_SCRIPT = Join-Path $AIMS_HOME "scripts\p0\Invoke-AimsOpenClawHostCli.ps1"
$PORTABLE_ENTRY = Join-Path $PORTABLE_ROOT "openclaw.mjs"

Set-Location $AIMS_HOME

if (-not (Test-Path -LiteralPath $HELPER_SCRIPT)) {
    throw "Host CLI helper not found: $HELPER_SCRIPT"
}

if (-not (Test-Path -LiteralPath $PORTABLE_ENTRY)) {
    throw "Portable OpenClaw entry not found: $PORTABLE_ENTRY"
}

Write-Host "Starting OpenClaw with OPENCLAW_HOME: $OPENCLAW_HOME"
Write-Host "Portable root: $PORTABLE_ROOT"
Write-Host "Env file: $ENV_PATH"

& $HELPER_SCRIPT -PortableRoot $PORTABLE_ROOT -EnvPath $ENV_PATH -HomeRoot $OPENCLAW_HOME -OpenClawArgs @("gateway", "run")
exit $LASTEXITCODE
