<#
AIMS AI Marketing System - OpenClaw Service Test Script
#>

$ErrorActionPreference = "Stop"

$AIMS_HOME = "D:\Project\aims"
$OPENCLAW_CONFIG = "$AIMS_HOME\openclaw.json"
$PORTABLE_ROOT = "D:\openclaw\openclaw-portable-win-x64"
$PORTABLE_ENTRY = Join-Path $PORTABLE_ROOT "openclaw.mjs"
$node = Get-Command node -ErrorAction SilentlyContinue

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "       OpenClaw Service Test Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check OpenClaw command
Write-Host "[Test 1] Checking OpenClaw installation..." -ForegroundColor Yellow
if ($null -eq $node) {
    Write-Host "FAIL: node.exe is not available on PATH" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $PORTABLE_ENTRY)) {
    Write-Host "FAIL: Portable OpenClaw entry not found at $PORTABLE_ENTRY" -ForegroundColor Red
    exit 1
}
Write-Host "OK: OpenClaw found at $PORTABLE_ENTRY" -ForegroundColor Green
Write-Host "Node: $($node.Source)"

$version = & node $PORTABLE_ENTRY --version 2>&1
Write-Host "Version: $version"
Write-Host ""

# Test 2: Check configuration file
Write-Host "[Test 2] Checking configuration file..." -ForegroundColor Yellow
if (-not (Test-Path $OPENCLAW_CONFIG)) {
    Write-Host "FAIL: Configuration file not found at $OPENCLAW_CONFIG" -ForegroundColor Red
    exit 1
}
Write-Host "OK: Configuration file found" -ForegroundColor Green
Write-Host ""

# Test 3: Validate configuration syntax
Write-Host "[Test 3] Validating configuration syntax..." -ForegroundColor Yellow
try {
    $configContent = Get-Content $OPENCLAW_CONFIG -Raw
    $json = $configContent | ConvertFrom-Json -ErrorAction Stop
    Write-Host "OK: Configuration JSON is valid" -ForegroundColor Green
    Write-Host "  - Agents defined: $($json.agents.list.Count)"
    Write-Host "  - Models configured: $($json.models.providers.PSObject.Properties.Name -join ', ')"
    Write-Host "  - Channels enabled: $($json.channels.PSObject.Properties.Name.Where({ $_ -ne 'defaults' }) -join ', ')"
} catch {
    Write-Host "FAIL: Configuration validation failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 4: Check workspace directories
Write-Host "[Test 4] Checking workspace directories..." -ForegroundColor Yellow
$workspaces = @("workspace-main", "workspace-ecommerce", "workspace-social", "workspace-cs", "workspace-office")
$allExists = $true

foreach ($ws in $workspaces) {
    $wsPath = "$AIMS_HOME\$ws"
    if (Test-Path $wsPath) {
        Write-Host "OK: $ws" -ForegroundColor Green
    } else {
        Write-Host "FAIL: $ws not found" -ForegroundColor Red
        $allExists = $false
    }
}

if (-not $allExists) {
    exit 1
}
Write-Host ""

# Test 5: Check environment file
Write-Host "[Test 5] Checking environment file..." -ForegroundColor Yellow
if (Test-Path "$AIMS_HOME\.env") {
    Write-Host "OK: .env file exists" -ForegroundColor Green
} else {
    Write-Host "WARN: .env file not found" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "           All tests completed successfully!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start OpenClaw service, run:" -ForegroundColor Gray
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$AIMS_HOME\start-aims.ps1`" -Choice 1" -ForegroundColor Gray
