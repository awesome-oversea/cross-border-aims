param(
    [string]$PortableRoot = "D:\openclaw\openclaw-portable-win-x64",
    [string]$EnvPath,
    [string]$HomeRoot,
    [int]$ReadyTimeoutSeconds = 120,
    [switch]$ForceRestart
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$envPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
$homeRoot = if ($HomeRoot) { $HomeRoot } else { Join-Path $repoRoot ".generated\openclaw-host-home" }
$helperScript = Join-Path $PSScriptRoot "Invoke-AimsOpenClawHostCli.ps1"
$pidFile = Join-Path $repoRoot ".generated\aims.host-gateway.pid"
$stdoutPath = Join-Path $repoRoot ".generated\aims.host-gateway.stdout.log"
$stderrPath = Join-Path $repoRoot ".generated\aims.host-gateway.stderr.log"
$envMap = Read-AimsDotEnv -Path $envPath
$gatewayPort = [int](Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_GATEWAY_PORT" -Default "18789")

function Test-GatewayListening {
    param(
        [int]$Port
    )

    try {
        $response = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/healthz" -f $Port) -UseBasicParsing -TimeoutSec 5
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
    }
    catch {
        return $false
    }
}

function Stop-GatewayProcess {
    param(
        [int]$ProcessId,
        [string]$Reason
    )

    if ($ProcessId -le 0) {
        return
    }

    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
    }
    catch {
        return
    }

    if ($process.ProcessName -notin @("node", "powershell", "pwsh")) {
        throw ("Refusing to stop unexpected process '{0}' (pid {1}) while handling {2}." -f $process.ProcessName, $ProcessId, $Reason)
    }

    Stop-Process -Id $ProcessId -Force -ErrorAction Stop
}

function Clear-StaleGatewayLocks {
    param(
        [string]$ConfigPath
    )

    $lockRoot = Join-Path $repoRoot "runtime\tmp\openclaw"
    if (-not (Test-Path -LiteralPath $lockRoot)) {
        return
    }

    foreach ($lockFile in Get-ChildItem -Path $lockRoot -Filter "gateway*.lock" -File -ErrorAction SilentlyContinue) {
        try {
            $payload = Get-Content -LiteralPath $lockFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        }
        catch {
            continue
        }

        $lockPid = 0
        if ($payload.PSObject.Properties.Name -contains "pid") {
            $lockPid = [int]$payload.pid
        }

        $lockConfigPath = ""
        if ($payload.PSObject.Properties.Name -contains "configPath") {
            $lockConfigPath = [string]$payload.configPath
        }

        $processAlive = $false
        if ($lockPid -gt 0) {
            try {
                Get-Process -Id $lockPid -ErrorAction Stop | Out-Null
                $processAlive = $true
            }
            catch {
            }
        }

        $configMatches = [string]::IsNullOrWhiteSpace($lockConfigPath) -or
            [string]::Equals($lockConfigPath, $ConfigPath, [System.StringComparison]::OrdinalIgnoreCase)

        if ((-not $processAlive) -and $configMatches) {
            Remove-Item -LiteralPath $lockFile.FullName -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($ForceRestart -and (Test-Path -LiteralPath $pidFile)) {
    try {
        $existingPid = [int](Get-Content -LiteralPath $pidFile -Raw)
        Stop-GatewayProcess -ProcessId $existingPid -Reason "pid file"
    }
    catch {
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

if ($ForceRestart -and (Test-GatewayListening -Port $gatewayPort)) {
    $portOwner = Get-NetTCPConnection -LocalPort $gatewayPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $portOwner) {
        Stop-GatewayProcess -ProcessId $portOwner.OwningProcess -Reason ("port {0}" -f $gatewayPort)
        Start-Sleep -Seconds 2
    }
}

if (Test-GatewayListening -Port $gatewayPort) {
    Write-Host ("Gateway already listening on port {0}" -f $gatewayPort)
    exit 0
}

$generatedDir = Split-Path -Parent $pidFile
if (-not (Test-Path -LiteralPath $generatedDir)) {
    New-Item -ItemType Directory -Path $generatedDir -Force | Out-Null
}

& (Join-Path $PSScriptRoot "Sync-AimsOpenClawHostHome.ps1") -EnvPath $envPath -HomeRoot $homeRoot | Out-Null
if (-not $?) {
    throw "Failed to sync host OpenClaw home."
}

Clear-StaleGatewayLocks -ConfigPath (Join-Path $homeRoot ".openclaw\openclaw.json")

$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $helperScript,
    "-PortableRoot", $PortableRoot,
    "-EnvPath", $envPath,
    "-HomeRoot", $homeRoot,
    "-RunGateway"
)

$process = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WorkingDirectory $repoRoot -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ASCII

$deadline = (Get-Date).AddSeconds($ReadyTimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    if ($process.HasExited) {
        $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { "" }
        $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { "" }
        $stdoutText = [string]$stdout
        $stderrText = [string]$stderr
        $stdoutText = if ($null -eq $stdoutText) { "" } else { $stdoutText.Trim() }
        $stderrText = if ($null -eq $stderrText) { "" } else { $stderrText.Trim() }
        throw ("Host gateway exited early. Stdout: {0}`nStderr: {1}" -f $stdoutText, $stderrText)
    }
    if (Test-GatewayListening -Port $gatewayPort) {
        Write-Host ("Host gateway started on port {0} (pid {1})" -f $gatewayPort, $process.Id)
        exit 0
    }
}
while ((Get-Date) -lt $deadline)

throw ("Host gateway did not become ready on port {0} within {1} seconds." -f $gatewayPort, $ReadyTimeoutSeconds)
