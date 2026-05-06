param(
    [Parameter(Mandatory = $true)]
    [string]$BashCommand,
    [string]$Distro = "Ubuntu-22.04",
    [ValidateSet("auto", "bash", "sh")]
    [string]$Shell = "auto",
    [switch]$CaptureStderr
)

$ErrorActionPreference = "Stop"

function Invoke-Wsl {
    param(
        [string[]]$ArgumentList
    )

    $output = if ($CaptureStderr) {
        & wsl.exe @ArgumentList 2>&1
    }
    else {
        & wsl.exe @ArgumentList
    }

    return [pscustomobject]@{
        Output   = $output
        ExitCode = $LASTEXITCODE
    }
}

$selectedShell = $Shell
if ($selectedShell -eq "auto") {
    $probe = Invoke-Wsl -ArgumentList @("-d", $Distro, "--", "sh", "-lc", "if command -v bash >/dev/null 2>&1; then printf bash; else printf sh; fi")
    if ($probe.ExitCode -ne 0) {
        $probeOutput = ($probe.Output | Out-String).Trim()
        throw "Unable to determine an available shell inside distro '$Distro'. $probeOutput"
    }

    $selectedShell = ($probe.Output | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($selectedShell)) {
        $selectedShell = "sh"
    }
}

$result = Invoke-Wsl -ArgumentList @("-d", $Distro, "--", $selectedShell, "-lc", $BashCommand)
$output = $result.Output
$exitCode = $result.ExitCode

if ($output) {
    Write-Output ($output | Out-String).Trim()
}

exit $exitCode
