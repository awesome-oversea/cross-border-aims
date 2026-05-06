param(
    [int]$TimeoutSeconds = 15,
    [string]$DockerDesktopDistro = "docker-desktop"
)

$ErrorActionPreference = "Stop"

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
            Stop-Process -Id $process.Id -Force
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

function Get-WslDistroDetail {
    param(
        [string]$Distro,
        [int]$Seconds
    )

    $listProbe = Invoke-ExternalWithTimeout -FilePath "wsl.exe" -ArgumentList @("-l", "-q") -Seconds $Seconds
    if ($listProbe.TimedOut) {
        return [pscustomobject]@{
            Passed = $false
            Detail = "wsl -l -q timed out"
        }
    }

    $listOutput = (($listProbe.StdOut + $listProbe.StdErr) -replace [char]0, "").Trim()
    if ($listProbe.ExitCode -ne 0) {
        return [pscustomobject]@{
            Passed = $false
            Detail = $listOutput
        }
    }

    $distroList = @($listOutput -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($Distro -notin $distroList) {
        return [pscustomobject]@{
            Passed = $false
            Detail = "distro '$Distro' not found"
        }
    }

    $detailProbe = Invoke-ExternalWithTimeout -FilePath "wsl.exe" -ArgumentList @("-l", "-v") -Seconds $Seconds
    if ($detailProbe.TimedOut) {
        return [pscustomobject]@{
            Passed = $true
            Detail = "$Distro present (detail probe timed out)"
        }
    }

    $detailOutput = (($detailProbe.StdOut + $detailProbe.StdErr) -replace [char]0, "").Trim()
    if ($detailProbe.ExitCode -ne 0) {
        return [pscustomobject]@{
            Passed = $true
            Detail = "$Distro present"
        }
    }

    $line = @($detailOutput -split "`r?`n" | Where-Object { $_ -match [regex]::Escape($Distro) } | Select-Object -First 1)
    if ($line.Count -eq 0) {
        return [pscustomobject]@{
            Passed = $true
            Detail = "$Distro present"
        }
    }

    return [pscustomobject]@{
        Passed = $true
        Detail = $line[0].Trim()
    }
}

function Get-WslShellDetail {
    param(
        [string]$Distro,
        [int]$Seconds
    )

    $probe = Invoke-ExternalWithTimeout -FilePath "wsl.exe" -ArgumentList @("-d", $Distro, "--", "sh", "-c", "command -v bash >/dev/null 2>&1 && printf bash || printf sh") -Seconds $Seconds
    if ($probe.TimedOut) {
        return [pscustomobject]@{
            Passed = $false
            Detail = "timed out while probing shell availability"
        }
    }

    $output = ($probe.StdOut + $probe.StdErr).Trim()
    if ($probe.ExitCode -ne 0 -and [string]::IsNullOrWhiteSpace($output)) {
        return [pscustomobject]@{
            Passed = $false
            Detail = $output
        }
    }

    return [pscustomobject]@{
        Passed = (-not [string]::IsNullOrWhiteSpace($output))
        Detail = if ([string]::IsNullOrWhiteSpace($output)) { "no shell reported" } else { $output }
    }
}

function Get-WslSocketDetail {
    param(
        [string]$Distro,
        [int]$Seconds
    )

    $probe = Invoke-ExternalWithTimeout -FilePath "wsl.exe" -ArgumentList @("-d", $Distro, "--", "sh", "-c", "[ -S /var/run/docker.sock ] && echo docker-sock-present || echo docker-sock-missing") -Seconds $Seconds
    if ($probe.TimedOut) {
        return [pscustomobject]@{
            Passed = $false
            Detail = "timed out while probing /var/run/docker.sock"
        }
    }

    $output = ($probe.StdOut + $probe.StdErr).Trim()
    return [pscustomobject]@{
        Passed = (-not $probe.TimedOut -and -not [string]::IsNullOrWhiteSpace($output))
        Detail = $output
    }
}

$dockerCommand = Get-Command docker.exe -ErrorAction Stop
$dockerPath = $dockerCommand.Source
$service = Get-Service -Name com.docker.service -ErrorAction SilentlyContinue
$lxssManager = Get-Service -Name LxssManager -ErrorAction SilentlyContinue

Add-Result -Name "docker.exe found" -Passed $true -Detail $dockerPath
Add-Result -Name "com.docker.service" -Passed ($null -ne $service) -Detail ($(if ($service) { $service.Status } else { "missing" }))
Add-Result -Name "LxssManager" -Passed ($null -ne $lxssManager -and $lxssManager.Status -eq "Running") -Detail ($(if ($lxssManager) { $lxssManager.Status } else { "missing" }))
Add-Result -Name "docker_engine pipe" -Passed (Test-Path "\\.\pipe\docker_engine") -Detail "\\.\pipe\docker_engine"
Add-Result -Name "dockerDesktopLinuxEngine pipe" -Passed (Test-Path "\\.\pipe\dockerDesktopLinuxEngine") -Detail "\\.\pipe\dockerDesktopLinuxEngine"

$dockerDesktopShell = Get-WslShellDetail -Distro $DockerDesktopDistro -Seconds ([Math]::Min($TimeoutSeconds, 10))
$dockerDesktopSocket = Get-WslSocketDetail -Distro $DockerDesktopDistro -Seconds ([Math]::Min($TimeoutSeconds, 10))

$dockerDesktopStatus = Get-WslDistroDetail -Distro $DockerDesktopDistro -Seconds ([Math]::Min($TimeoutSeconds, 10))
if (-not $dockerDesktopStatus.Passed -and $dockerDesktopShell.Passed) {
    $dockerDesktopStatus = [pscustomobject]@{
        Passed = $true
        Detail = "$DockerDesktopDistro reachable via wsl.exe"
    }
}

Add-Result -Name "$DockerDesktopDistro distro" -Passed $dockerDesktopStatus.Passed -Detail $dockerDesktopStatus.Detail
Add-Result -Name "$DockerDesktopDistro shell" -Passed $dockerDesktopShell.Passed -Detail $dockerDesktopShell.Detail
Add-Result -Name "$DockerDesktopDistro docker.sock" -Passed $dockerDesktopSocket.Passed -Detail $dockerDesktopSocket.Detail

$clientVersion = Invoke-ExternalWithTimeout -FilePath $dockerPath -ArgumentList @("--version") -Seconds $TimeoutSeconds
$clientVersionDetail = if ($clientVersion.TimedOut) { "timed out" } else { (Join-CommandOutput -StdOut $clientVersion.StdOut -StdErr $clientVersion.StdErr) }
Add-Result -Name "docker client version" -Passed (-not $clientVersion.TimedOut -and -not [string]::IsNullOrWhiteSpace($clientVersionDetail) -and $clientVersionDetail -match "^Docker version") -Detail $clientVersionDetail

$contextShow = Invoke-ExternalWithTimeout -FilePath $dockerPath -ArgumentList @("context", "show") -Seconds $TimeoutSeconds
$contextDetail = if ($contextShow.TimedOut) { "timed out" } else { (Join-CommandOutput -StdOut $contextShow.StdOut -StdErr $contextShow.StdErr) }
Add-Result -Name "docker context show" -Passed (-not $contextShow.TimedOut -and -not [string]::IsNullOrWhiteSpace($contextDetail)) -Detail $contextDetail

$serverVersion = Invoke-ExternalWithTimeout -FilePath $dockerPath -ArgumentList @("version", "--format", "{{.Server.Version}}") -Seconds $TimeoutSeconds
$serverVersionDetail = if ($serverVersion.TimedOut) { "timed out while waiting for daemon response" } else { (Join-CommandOutput -StdOut $serverVersion.StdOut -StdErr $serverVersion.StdErr) }
Add-Result -Name "docker server version" -Passed (Test-HealthyCliResult -Probe $serverVersion -Detail $serverVersionDetail) -Detail $serverVersionDetail

$dockerPs = Invoke-ExternalWithTimeout -FilePath $dockerPath -ArgumentList @("ps", "--format", "{{.Names}}") -Seconds $TimeoutSeconds
$dockerPsDetail = if ($dockerPs.TimedOut) { "timed out while waiting for daemon response" } else { (Join-CommandOutput -StdOut $dockerPs.StdOut -StdErr $dockerPs.StdErr) }
Add-Result -Name "docker ps" -Passed (Test-HealthyCliResult -Probe $dockerPs -Detail $dockerPsDetail) -Detail $dockerPsDetail

$backendLog = Join-Path $env:LOCALAPPDATA "Docker\log\host\com.docker.backend.exe.log"
$monitorLog = Join-Path $env:LOCALAPPDATA "Docker\log\host\monitor.log"

if (Test-Path -LiteralPath $backendLog) {
    $backendFile = Get-Item -LiteralPath $backendLog
    Add-Note ("backend log last write: {0} ({1})" -f $backendFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), $backendLog)
}

if (Test-Path -LiteralPath $monitorLog) {
    $monitorFile = Get-Item -LiteralPath $monitorLog
    Add-Note ("monitor log last write: {0} ({1})" -f $monitorFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), $monitorLog)
}

$failedDaemonChecks = @($results | Where-Object { $_.Name -in @("docker server version", "docker ps", "$DockerDesktopDistro docker.sock") -and $_.Status -eq "FAIL" })
if ($failedDaemonChecks.Count -gt 0 -and (Test-Path -LiteralPath $monitorLog)) {
    foreach ($line in @(Get-Content -LiteralPath $monitorLog -Tail 5 -ErrorAction SilentlyContinue)) {
        Add-Note ("monitor tail: " + $line)
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
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
