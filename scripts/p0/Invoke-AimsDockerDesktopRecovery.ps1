param(
    [int]$ReadyTimeoutSeconds = 180,
    [int]$CliTimeoutSeconds = 15,
    [switch]$SkipWslShutdown
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$results = New-Object System.Collections.Generic.List[object]
$notes = New-Object System.Collections.Generic.List[string]

function Add-Result {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )

    $results.Add([pscustomobject]@{
        Status = if ($Passed) { "PASS" } else { "FAIL" }
        Name   = $Name
        Detail = $Detail
    })
}

function Add-Note {
    param(
        [string]$Detail
    )

    if (-not [string]::IsNullOrWhiteSpace($Detail)) {
        $notes.Add($Detail)
    }
}

function Join-CommandOutput {
    param(
        [object]$StdOut,
        [object]$StdErr
    )

    return ((([string]$StdOut) + ([string]$StdErr)).Trim())
}

function Test-HealthyCliResult {
    param(
        [object]$Probe,
        [string]$Detail
    )

    if ($Probe.TimedOut) {
        return $false
    }

    if ($Probe.ExitCode -eq 0) {
        return $true
    }

    if ([string]::IsNullOrWhiteSpace($Detail)) {
        return $false
    }

    $normalized = $Detail.ToLowerInvariant()
    foreach ($keyword in @("error", "denied", "timeout", "unable", "cannot", "failed", "refused")) {
        if ($normalized.Contains($keyword)) {
            return $false
        }
    }

    return $true
}

function Invoke-ExternalWithTimeout {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [int]$Seconds
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -NoNewWindow -PassThru
        $completed = $process.WaitForExit($Seconds * 1000)

        if (-not $completed) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            return [pscustomobject]@{
                TimedOut = $true
                ExitCode = -1
                StdOut   = (Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue)
                StdErr   = (Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue)
            }
        }

        return [pscustomobject]@{
            TimedOut = $false
            ExitCode = $process.ExitCode
            StdOut   = (Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue)
            StdErr   = (Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue)
        }
    }
    finally {
        Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    }
}

function Stop-DockerDesktopProcesses {
    $names = @(
        "Docker Desktop",
        "com.docker.backend",
        "com.docker.build",
        "com.docker.proxy",
        "vpnkit"
    )

    $processes = @(Get-Process -Name $names -ErrorAction SilentlyContinue)
    foreach ($process in $processes) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }

    return $processes.Count
}

function Test-DockerServerReady {
    param(
        [string]$DockerPath,
        [int]$Seconds
    )

    $server = Invoke-ExternalWithTimeout -FilePath $DockerPath -ArgumentList @("version", "--format", "{{.Server.Version}}") -Seconds $Seconds
    if ($server.TimedOut) {
        return [pscustomobject]@{
            Passed = $false
            Detail = "docker server version timed out"
        }
    }

    $serverDetail = Join-CommandOutput -StdOut $server.StdOut -StdErr $server.StdErr
    if (-not (Test-HealthyCliResult -Probe $server -Detail $serverDetail)) {
        return [pscustomobject]@{
            Passed = $false
            Detail = $serverDetail
        }
    }

    $dockerPs = Invoke-ExternalWithTimeout -FilePath $DockerPath -ArgumentList @("ps", "--format", "{{.Names}}") -Seconds $Seconds
    if ($dockerPs.TimedOut) {
        return [pscustomobject]@{
            Passed = $false
            Detail = "docker ps timed out after server version became available"
        }
    }

    $dockerPsDetail = Join-CommandOutput -StdOut $dockerPs.StdOut -StdErr $dockerPs.StdErr
    if (-not (Test-HealthyCliResult -Probe $dockerPs -Detail $dockerPsDetail)) {
        return [pscustomobject]@{
            Passed = $false
            Detail = $dockerPsDetail
        }
    }

    $detail = "Server " + $server.StdOut.Trim()
    $names = ($dockerPs.StdOut.Trim())
    if (-not [string]::IsNullOrWhiteSpace($names)) {
        $detail += "; containers: " + $names
    }

    return [pscustomobject]@{
        Passed = $true
        Detail = $detail
    }
}

$dockerPath = (Get-Command docker.exe -ErrorAction Stop).Source
$desktopExe = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"

if (-not (Test-Path -LiteralPath $desktopExe)) {
    throw "Docker Desktop executable not found: $desktopExe"
}

$initial = Test-DockerServerReady -DockerPath $dockerPath -Seconds $CliTimeoutSeconds
Add-Result -Name "docker server before recovery" -Passed $initial.Passed -Detail $initial.Detail

if ($initial.Passed) {
    $results | Format-Table -AutoSize
    exit 0
}

$killedCount = Stop-DockerDesktopProcesses
Add-Result -Name "stop Docker Desktop processes" -Passed $true -Detail ("stopped " + $killedCount + " process(es)")

$service = Get-Service -Name com.docker.service -ErrorAction SilentlyContinue
if ($null -eq $service) {
    Add-Result -Name "restart com.docker.service" -Passed $false -Detail "service missing"
}
else {
    try {
        if ($service.Status -eq "Running") {
            Stop-Service -Name com.docker.service -Force -ErrorAction Stop
            $service.WaitForStatus("Stopped", "00:00:30")
        }

        Start-Service -Name com.docker.service -ErrorAction Stop
        (Get-Service -Name com.docker.service).WaitForStatus("Running", "00:00:30")
        Add-Result -Name "restart com.docker.service" -Passed $true -Detail "Running"
    }
    catch {
        Add-Result -Name "restart com.docker.service" -Passed $false -Detail $_.Exception.Message
    }
}

if (-not $SkipWslShutdown) {
    $shutdown = Invoke-ExternalWithTimeout -FilePath "wsl.exe" -ArgumentList @("--shutdown") -Seconds ([Math]::Max($CliTimeoutSeconds, 10))
    $shutdownDetail = Join-CommandOutput -StdOut $shutdown.StdOut -StdErr $shutdown.StdErr
    if ([string]::IsNullOrWhiteSpace($shutdownDetail)) {
        $shutdownDetail = "WSL distributions requested to shut down"
    }

    Add-Result -Name "wsl --shutdown" -Passed (-not $shutdown.TimedOut) -Detail $(if ($shutdown.TimedOut) { "timed out" } else { $shutdownDetail })
}
else {
    Add-Note "Skipped WSL shutdown by request."
}

try {
    $started = Start-Process -FilePath $desktopExe -PassThru
    Add-Result -Name "start Docker Desktop" -Passed $true -Detail ("pid " + $started.Id)
}
catch {
    Add-Result -Name "start Docker Desktop" -Passed $false -Detail $_.Exception.Message
}

$deadline = (Get-Date).AddSeconds($ReadyTimeoutSeconds)
$ready = [pscustomobject]@{
    Passed = $false
    Detail = "docker daemon did not become ready"
}

do {
    Start-Sleep -Seconds 5
    $ready = Test-DockerServerReady -DockerPath $dockerPath -Seconds $CliTimeoutSeconds
    if ($ready.Passed) {
        break
    }
}
while ((Get-Date) -lt $deadline)

Add-Result -Name "docker server after recovery" -Passed $ready.Passed -Detail $ready.Detail

if (-not $ready.Passed) {
    $logPaths = @(
        (Join-Path $env:LOCALAPPDATA "Docker\log\host\com.docker.backend.exe.log"),
        (Join-Path $env:LOCALAPPDATA "Docker\log\host\monitor.log")
    )

    foreach ($logPath in $logPaths) {
        if (-not (Test-Path -LiteralPath $logPath)) {
            continue
        }

        $file = Get-Item -LiteralPath $logPath
        Add-Note ("log last write: {0} ({1})" -f $file.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), $logPath)
        foreach ($line in @(Get-Content -LiteralPath $logPath -Tail 3 -ErrorAction SilentlyContinue)) {
            Add-Note ("log tail: " + $line)
        }
    }
}

$results | Format-Table -AutoSize

if ($notes.Count -gt 0) {
    Write-Host ""
    Write-Host "Notes:" -ForegroundColor Yellow
    foreach ($note in $notes) {
        Write-Host ("- " + $note) -ForegroundColor Yellow
    }
}

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($ready.Passed) {
    $failed = @($failed | Where-Object { $_.Name -ne "docker server before recovery" })
}

if ($failed.Count -gt 0) {
    exit 1
}

exit 0
