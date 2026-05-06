<#
AIMS AI Marketing System - Windows PowerShell Startup Script
All paths locked to D: drive, no C: drive writes
#>

param(
    [int]$Choice = 0
)

$ErrorActionPreference = "Stop"

$AIMS_HOME = "D:\Project\aims"
$OPENCLAW_HOME = Join-Path $AIMS_HOME ".generated\openclaw-host-home"
$OPENCLAW_CONFIG = Join-Path $AIMS_HOME "openclaw.json"
$PORTABLE_ROOT = "D:\openclaw\openclaw-portable-win-x64"
$PORTABLE_ENTRY = Join-Path $PORTABLE_ROOT "openclaw.mjs"
$HOST_GATEWAY_SCRIPT = Join-Path $AIMS_HOME "scripts\p0\Start-AimsGatewayHost.ps1"
$HOST_CLI_SCRIPT = Join-Path $AIMS_HOME "scripts\p0\Invoke-AimsOpenClawHostCli.ps1"
$ENV_PATH = Join-Path $AIMS_HOME ".env"

Set-Location $AIMS_HOME -ErrorAction SilentlyContinue

function Write-Header {
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "        AIMS AI Marketing System" -ForegroundColor Cyan
    Write-Host "         Windows Startup Script" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "All paths locked to D: drive, no C: drive writes" -ForegroundColor Gray
    Write-Host ""
}

function Write-SystemCheck {
    Write-Host "System Check:" -ForegroundColor Yellow
    Write-Host "- AIMS_HOME: $AIMS_HOME"
    Write-Host "- OPENCLAW_HOME: $OPENCLAW_HOME"
    Write-Host "- OPENCLAW_CONFIG: $OPENCLAW_CONFIG"
    Write-Host "- PORTABLE_ROOT: $PORTABLE_ROOT"
    Write-Host ""
}

function Test-OpenClaw {
    if (-not (Test-Path -LiteralPath $HOST_GATEWAY_SCRIPT)) {
        Write-Host "ERROR: Host gateway script not found at $HOST_GATEWAY_SCRIPT" -ForegroundColor Red
        exit 1
    }

    if (-not (Test-Path -LiteralPath $HOST_CLI_SCRIPT)) {
        Write-Host "ERROR: Host CLI script not found at $HOST_CLI_SCRIPT" -ForegroundColor Red
        exit 1
    }

    if (-not (Test-Path -LiteralPath $PORTABLE_ENTRY)) {
        Write-Host "ERROR: Portable OpenClaw entry not found at $PORTABLE_ENTRY" -ForegroundColor Red
        Write-Host "INFO: Confirm the portable bundle exists under D:\\openclaw\\openclaw-portable-win-x64" -ForegroundColor Yellow
        exit 1
    }

    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) {
        Write-Host "ERROR: node.exe is not available on PATH" -ForegroundColor Red
        exit 1
    }

    $version = & node $PORTABLE_ENTRY --version 2>&1
    Write-Host "OpenClaw found: $PORTABLE_ENTRY" -ForegroundColor Green
    Write-Host "Node: $($node.Source)"
    Write-Host "OpenClaw Version: $version"
    Write-Host ""
}

function Show-Menu {
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "              Startup Options" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "1. Start OpenClaw Host Gateway"
    Write-Host "2. Run OpenClaw Gateway (Debug Foreground)"
    Write-Host "3. Start Docker Dependencies (Test)"
    Write-Host "4. Validate Environment"
    Write-Host "5. Exit"
    Write-Host "================================================" -ForegroundColor Cyan
}

function Invoke-ValidateEnvironment {
    Write-Host "Validating Environment..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "--- Directory Check ---" -ForegroundColor Yellow

    $paths = @(
        "workspace-main",
        "workspace-ecommerce",
        "workspace-social",
        "workspace-cs",
        "workspace-office",
        "skills",
        "scripts\p0\Start-AimsGatewayHost.ps1",
        "scripts\p0\Invoke-AimsOpenClawHostCli.ps1",
        "openclaw.json",
        ".env"
    )

    foreach ($path in $paths) {
        if (Test-Path $path) {
            Write-Host "[OK] $path" -ForegroundColor Green
        }
        else {
            Write-Host "[MISSING] $path" -ForegroundColor Red
        }
    }

    Write-Host ""
}

function Start-OpenClawService {
    param([string]$Mode = "normal")

    if ($Mode -eq "debug") {
        Write-Host "Running OpenClaw Gateway in foreground debug mode..." -ForegroundColor Yellow
        & $HOST_CLI_SCRIPT -PortableRoot $PORTABLE_ROOT -EnvPath $ENV_PATH -HomeRoot $OPENCLAW_HOME -OpenClawArgs @("gateway", "run", "--verbose")
        exit $LASTEXITCODE
    }

    Write-Host "Starting OpenClaw Host Gateway..." -ForegroundColor Yellow
    & $HOST_GATEWAY_SCRIPT -PortableRoot $PORTABLE_ROOT -EnvPath $ENV_PATH -HomeRoot $OPENCLAW_HOME
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Header
Write-SystemCheck
Test-OpenClaw

if ($Choice -eq 0) {
    Show-Menu
    $Choice = Read-Host "Enter your choice [1-5]"
}

switch ($Choice) {
    1 {
        Start-OpenClawService -Mode "normal"
    }
    2 {
        Start-OpenClawService -Mode "debug"
    }
    3 {
        Write-Host "Starting Docker Dependencies..." -ForegroundColor Yellow
        if (-not (Test-Path "docker-compose.yml")) {
            Write-Host "ERROR: docker-compose.yml not found" -ForegroundColor Red
            exit 1
        }
        docker compose up -d
        Write-Host "Docker services started" -ForegroundColor Green
    }
    4 {
        Invoke-ValidateEnvironment
    }
    5 {
        Write-Host "Exiting..." -ForegroundColor Gray
        exit 0
    }
    default {
        Write-Host "Invalid choice: $Choice" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Operation completed" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
