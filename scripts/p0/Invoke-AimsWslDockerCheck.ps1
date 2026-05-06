param(
    [string]$Distro,
    [string]$WslToolsRoot = "/mnt/d/aitools",
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$results = New-Object System.Collections.Generic.List[object]

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

function Invoke-WslCapture {
    param(
        [string]$Command
    )

    $args = @()
    if (-not [string]::IsNullOrWhiteSpace($Distro)) {
        $args += @("-d", $Distro)
    }
    $args += @("bash", "-lc", $Command)

    $output = & wsl.exe @args 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output   = ($output | Out-String).Trim()
    }
}

$wslCommand = Get-Command wsl.exe -ErrorAction SilentlyContinue
Add-Result -Name "wsl.exe available" -Passed ($null -ne $wslCommand) -Detail $(if ($wslCommand) { $wslCommand.Source } else { "missing" })

if ($null -eq $wslCommand) {
    $results | Format-Table -AutoSize
    exit 1
}

$distroList = & wsl.exe -l -q 2>&1
$distroText = (($distroList | Out-String) -replace "`0", "").Trim()
Add-Result -Name "wsl distro list" -Passed ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($distroText)) -Detail $distroText

if (-not [string]::IsNullOrWhiteSpace($Distro)) {
    Add-Result -Name "requested distro present" -Passed ($distroText -match [regex]::Escape($Distro)) -Detail $Distro
}

$repoPathCheck = Invoke-WslCapture -Command ("test -d " + "'" + (([string]$repoRoot).Replace("\", "/") -replace "^([A-Za-z]):", { "/mnt/" + $_.Groups[1].Value.ToLowerInvariant() }) + "'")
if ($repoPathCheck.ExitCode -ne 0) {
    $repoWslPath = "/mnt/" + $repoRoot.Substring(0, 1).ToLowerInvariant() + $repoRoot.Substring(2).Replace("\", "/")
    $repoPathCheck = Invoke-WslCapture -Command ("test -d " + "'" + $repoWslPath + "'")
    Add-Result -Name "repo visible in WSL" -Passed ($repoPathCheck.ExitCode -eq 0) -Detail $repoWslPath
}
else {
    Add-Result -Name "repo visible in WSL" -Passed $true -Detail $repoRoot
}

$toolsRootCheck = Invoke-WslCapture -Command ("mkdir -p " + "'" + $WslToolsRoot.TrimEnd("/") + "' && test -d " + "'" + $WslToolsRoot.TrimEnd("/") + "'")
Add-Result -Name "WSL tools root writable" -Passed ($toolsRootCheck.ExitCode -eq 0) -Detail $WslToolsRoot

$dockerVersion = Invoke-WslCapture -Command "command -v docker >/dev/null 2>&1 && docker version --format '{{.Client.Version}}'"
Add-Result -Name "docker CLI in WSL" -Passed ($dockerVersion.ExitCode -eq 0) -Detail $(if ($dockerVersion.Output) { $dockerVersion.Output } else { "docker command not available in WSL" })

$composeVersion = Invoke-WslCapture -Command "command -v docker >/dev/null 2>&1 && docker compose version --short"
Add-Result -Name "docker compose in WSL" -Passed ($composeVersion.ExitCode -eq 0) -Detail $(if ($composeVersion.Output) { $composeVersion.Output } else { "docker compose not available in WSL" })

$dockerReachable = Invoke-WslCapture -Command "command -v docker >/dev/null 2>&1 && docker info --format '{{.ServerVersion}}'"
Add-Result -Name "docker engine reachable from WSL" -Passed ($dockerReachable.ExitCode -eq 0) -Detail $(if ($dockerReachable.Output) { $dockerReachable.Output } else { "Docker Desktop WSL integration may be disabled" })

if ($AsJson) {
    [pscustomobject]@{
        distro       = [string]$Distro
        wslToolsRoot = [string]$WslToolsRoot
        results      = @($results | ForEach-Object {
            [pscustomobject]@{
                Status = [string]$_.Status
                Name   = [string]$_.Name
                Detail = [string]$_.Detail
            }
        })
    } | ConvertTo-Json -Depth 8
}
else {
    $results | Format-Table -AutoSize
}

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
