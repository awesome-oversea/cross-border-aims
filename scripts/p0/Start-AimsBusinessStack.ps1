param(
    [ValidateSet("Auto", "PrivateDocker", "SharedHost")]
    [string]$OllamaMode = "Auto",
    [ValidateSet("Auto", "Docker", "HostPortable")]
    [string]$GatewayMode = "Auto",
    [switch]$UseWsl,
    [string]$WslDistro,
    [switch]$StartGateway,
    [switch]$IncludeInfra,
    [switch]$PullModels,
    [switch]$WarmModelCaches,
    [switch]$ProbeGenerate,
    [switch]$UseMirrorRegistry,
    [string]$PortableRoot = "D:\openclaw\openclaw-portable-win-x64",
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"
$ollamaCheckScript = Join-Path $PSScriptRoot "Invoke-AimsOllamaCheck.ps1"
$localLlmHealthScript = Join-Path $PSScriptRoot "Invoke-AimsLocalLlmHealth.ps1"
$gatewayHealthScript = Join-Path $PSScriptRoot "Invoke-AimsGatewayHealth.ps1"
$preflightScript = Join-Path $PSScriptRoot "Invoke-AimsPreflight.ps1"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw ".env is missing. Run scripts/p0/Initialize-AimsEnv.ps1 first."
}

$envMap = Read-AimsDotEnv -Path $envPath
$privateDockerEndpoint = "http://ollama:11434"
$openClawImage = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_OPENCLAW_IMAGE" -Default "ghcr.io/openclaw/openclaw:latest"
$sharedHostContainerEndpoint = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_HOST_SHARED_OLLAMA_ENDPOINT" -Default "http://host.docker.internal:11434"
$sharedHostProbeEndpoint = Get-AimsEnvValueOrDefault -Map $envMap -Key "LLM_OLLAMA_ENDPOINT" -Default "http://localhost:11434"

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

function ConvertTo-BashLiteral {
    param(
        [string]$Value
    )

    return "'" + ([string]$Value).Replace("'", "'""'""'") + "'"
}

function Join-BashArguments {
    param(
        [string[]]$Values
    )

    return (($Values | ForEach-Object { ConvertTo-BashLiteral -Value $_ }) -join " ")
}

function Invoke-WslDockerCapture {
    param(
        [string[]]$Arguments
    )

    $wslArgs = @()
    if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
        $wslArgs += @("-d", $WslDistro)
    }

    $bashCommand = "docker " + (Join-BashArguments -Values $Arguments)
    $output = & wsl.exe @wslArgs bash -lc $bashCommand 2>&1

    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output   = ($output | Out-String).Trim()
    }
}

function Invoke-DockerCapture {
    param(
        [string[]]$Arguments,
        [int]$TimeoutSeconds = 15
    )

    if ($UseWsl) {
        return Invoke-WslDockerCapture -Arguments $Arguments
    }

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process -FilePath "docker.exe" -ArgumentList $Arguments -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $exited = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $exited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            return [pscustomobject]@{
                ExitCode = 124
                Output   = ("Timed out after {0}s: docker.exe {1}" -f $TimeoutSeconds, ($Arguments -join " "))
            }
        }

        $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { "" }
        $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { "" }

        return [pscustomobject]@{
            ExitCode = $process.ExitCode
            Output   = (@($stdout, $stderr) -join [System.Environment]::NewLine).Trim()
        }
    }
    catch {
        return [pscustomobject]@{
            ExitCode = 1
            Output   = $_.Exception.Message
        }
    }
    finally {
        Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
}

function Test-DockerImageExists {
    param(
        [string]$Image
    )

    $inspect = Invoke-DockerCapture -Arguments @("image", "inspect", $Image)
    return ($inspect.ExitCode -eq 0)
}

function Resolve-LocalDockerImageCandidate {
    param(
        [string]$PreferredImage,
        [string[]]$FallbackImages
    )

    $candidates = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in @($PreferredImage) + @($FallbackImages)) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        if (-not $candidates.Contains($candidate)) {
            $candidates.Add($candidate)
        }
    }

    foreach ($candidate in $candidates) {
        if (Test-DockerImageExists -Image $candidate) {
            return [pscustomobject]@{
                Exists = $true
                Image  = $candidate
            }
        }
    }

    return [pscustomobject]@{
        Exists = $false
        Image  = $(if ($candidates.Count -gt 0) { $candidates[0] } else { "" })
    }
}

function Test-PortableSupportsOllama {
    param(
        [string]$PortableRootPath
    )

    # The portable OpenClaw package is not a supported gateway for the AIMS
    # local-Ollama workflow. Keep auto detection disabled so startup fails
    # fast instead of falling back into a known broken path.
    return $false
}

function Resolve-GatewaySelection {
    param(
        [string]$RequestedMode,
        [string]$PortableRootPath,
        [string]$DockerImage
    )

    $portableCliPath = Join-Path $PortableRootPath "openclaw.mjs"
    $dockerImageAvailable = Test-DockerImageExists -Image $DockerImage
    $portableAvailable = Test-Path -LiteralPath $portableCliPath
    $portableSupportsOllama = if ($portableAvailable) {
        Test-PortableSupportsOllama -PortableRootPath $PortableRootPath
    }
    else {
        $false
    }

    switch ($RequestedMode) {
        "Docker" {
            return [pscustomobject]@{
                Passed = $dockerImageAvailable
                Mode   = "Docker"
                Detail = $(if ($dockerImageAvailable) {
                        "Using local Docker OpenClaw image $DockerImage."
                    }
                    else {
                        "Docker OpenClaw image is missing locally: $DockerImage. A one-time pull is required because the local portable package does not provide Ollama support."
                    })
            }
        }
        "HostPortable" {
            return [pscustomobject]@{
                Passed = $false
                Mode   = "HostPortable"
                Detail = $(if (-not $portableAvailable) {
                        "Portable OpenClaw entry not found: $portableCliPath"
                    }
                    else {
                        "Portable OpenClaw at $PortableRootPath is disabled for the local Ollama workflow. Use the Docker gateway image instead."
                    })
            }
        }
        default {
            if ($dockerImageAvailable) {
                return [pscustomobject]@{
                    Passed = $true
                    Mode   = "Docker"
                    Detail = "Auto selected Docker because the OpenClaw image already exists locally."
                }
            }

            return [pscustomobject]@{
                Passed = $false
                Mode   = "Unavailable"
                Detail = "Docker OpenClaw image is not available locally: $DockerImage. Pull it once or point AIMS_OPENCLAW_IMAGE at an existing local tag, then rerun the business stack."
            }
        }
    }
}

function Invoke-ScriptCapture {
    param(
        [string]$Path,
        [hashtable]$Parameters
    )

    if ($null -eq $Parameters -or $Parameters.Count -eq 0) {
        $output = & $Path 2>&1
    }
    else {
        $output = & $Path @Parameters 2>&1
    }

    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output   = ($output | Out-String).Trim()
    }
}

function Convert-CapturedJson {
    param(
        [string]$Text
    )

    $jsonStart = $Text.IndexOf("{")
    if ($jsonStart -lt 0) {
        return $null
    }

    return ($Text.Substring($jsonStart) | ConvertFrom-Json)
}

function Get-CheckResultPassed {
    param(
        [object]$Payload,
        [string]$Name
    )

    if ($null -eq $Payload) {
        return $false
    }

    $match = @($Payload.results | Where-Object { $_.Name -eq $Name } | Select-Object -First 1)
    if ($match.Count -eq 0) {
        return $false
    }

    return ($match[0].Status -eq "PASS")
}

function Get-CheckResultDetail {
    param(
        [object]$Payload,
        [string]$Name
    )

    if ($null -eq $Payload) {
        return "missing"
    }

    $match = @($Payload.results | Where-Object { $_.Name -eq $Name } | Select-Object -First 1)
    if ($match.Count -eq 0) {
        return "missing"
    }

    return [string]$match[0].Detail
}

$hostCheckParams = @{
    EnvPath  = $envPath
    Endpoint = $sharedHostProbeEndpoint
    AsJson   = $true
}
if ($ProbeGenerate) {
    $hostCheckParams["ProbeGenerate"] = $true
}
$hostCheckRaw = Invoke-ScriptCapture -Path $ollamaCheckScript -Parameters $hostCheckParams
$hostCheck = Convert-CapturedJson -Text $hostCheckRaw.Output
$hostPrimaryInstalled = Get-CheckResultPassed -Payload $hostCheck -Name "Primary model installed"
$hostEndpointReachable = Get-CheckResultPassed -Payload $hostCheck -Name "Ollama endpoint reachable"

$privateCheckParams = @{
    AsJson         = $true
    TimeoutSeconds = 15
}
if ($UseWsl) {
    $privateCheckParams["UseWsl"] = $true
    if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
        $privateCheckParams["WslDistro"] = $WslDistro
    }
}
if ($ProbeGenerate) {
    $privateCheckParams["ProbeGenerate"] = $true
}
$privateCheckRaw = Invoke-ScriptCapture -Path $localLlmHealthScript -Parameters $privateCheckParams
$privateCheck = Convert-CapturedJson -Text $privateCheckRaw.Output
$privatePrimaryInstalled = Get-CheckResultPassed -Payload $privateCheck -Name "ollama: Primary model installed"
$privateEndpointReachable = Get-CheckResultPassed -Payload $privateCheck -Name "ollama: Ollama endpoint reachable"

$effectiveMode = $OllamaMode
if ($OllamaMode -eq "Auto") {
    if ($privatePrimaryInstalled) {
        $effectiveMode = "PrivateDocker"
    }
    elseif ($hostPrimaryInstalled) {
        $effectiveMode = "SharedHost"
    }
    else {
        $effectiveMode = "PrivateDocker"
    }
}

$effectiveDockerEndpoint = if ($effectiveMode -eq "SharedHost") {
    $sharedHostContainerEndpoint
}
else {
    $privateDockerEndpoint
}

Set-AimsDotEnvValues -Path $envPath -Values @{
    AIMS_DOCKER_OLLAMA_ENDPOINT = $effectiveDockerEndpoint
    AIMS_HOST_SHARED_OLLAMA_ENDPOINT = $sharedHostContainerEndpoint
}

Add-Result -Name "shared host ollama reachable" -Passed ($hostEndpointReachable -or $effectiveMode -ne "SharedHost") -Detail $(if ($hostEndpointReachable) { Get-CheckResultDetail -Payload $hostCheck -Name "Ollama endpoint reachable" } else { "not selected" })
Add-Result -Name "shared host primary model" -Passed ($hostPrimaryInstalled -or $effectiveMode -ne "SharedHost") -Detail $(if ($hostPrimaryInstalled) { Get-CheckResultDetail -Payload $hostCheck -Name "Primary model installed" } else { "not selected" })
Add-Result -Name "private docker ollama reachable" -Passed ($privateEndpointReachable -or $effectiveMode -ne "PrivateDocker") -Detail $(if ($privateEndpointReachable) { Get-CheckResultDetail -Payload $privateCheck -Name "ollama: Ollama endpoint reachable" } else { "not selected" })
Add-Result -Name "private docker primary model" -Passed ($privatePrimaryInstalled -or $effectiveMode -ne "PrivateDocker") -Detail $(if ($privatePrimaryInstalled) { Get-CheckResultDetail -Payload $privateCheck -Name "ollama: Primary model installed" } else { "not selected" })
Add-Result -Name "selected ollama mode" -Passed $true -Detail $effectiveMode
Add-Result -Name "active docker ollama endpoint" -Passed $true -Detail $effectiveDockerEndpoint
Add-Result -Name ".env updated" -Passed $true -Detail $envPath

if ($effectiveMode -eq "PrivateDocker") {
    $localRunParams = @{
        AsJson         = $true
        TimeoutSeconds = $TimeoutSeconds
        StartServices  = $true
    }
    if ($UseWsl) {
        $localRunParams["UseWsl"] = $true
        if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
            $localRunParams["WslDistro"] = $WslDistro
        }
    }
    if ($PullModels) {
        $localRunParams["PullModels"] = $true
    }

    if ($WarmModelCaches) {
        $localRunParams["WarmModelCaches"] = $true
    }

    if ($ProbeGenerate) {
        $localRunParams["ProbeGenerate"] = $true
    }

    $privateRunRaw = Invoke-ScriptCapture -Path $localLlmHealthScript -Parameters $localRunParams
    $privateRun = Convert-CapturedJson -Text $privateRunRaw.Output

    if ($null -eq $privateRun) {
        Add-Result -Name "private docker bootstrap output" -Passed $false -Detail $privateRunRaw.Output
    }
    else {
        foreach ($item in @($privateRun.results)) {
            Add-Result -Name ("private docker: " + $item.Name) -Passed ($item.Status -eq "PASS") -Detail ([string]$item.Detail)
        }
    }
}
elseif ($PullModels -or $WarmModelCaches) {
    Add-Result -Name "shared host skips private bootstrap" -Passed $true -Detail "Ignoring -PullModels / -WarmModelCaches because SharedHost mode uses the existing host Ollama instance."
}

$preflightParams = @{
    CheckOllama = $true
}
if ($UseWsl) {
    $preflightParams["UseWsl"] = $true
    $preflightParams["CheckWsl"] = $true
    if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
        $preflightParams["WslDistro"] = $WslDistro
    }
}
if ($effectiveMode -eq "PrivateDocker") {
    $preflightParams["UseLocalLlm"] = $true
}
if ($UseMirrorRegistry) {
    $preflightParams["UseMirrorRegistry"] = $true
}
$preflightRaw = Invoke-ScriptCapture -Path $preflightScript -Parameters $preflightParams
Add-Result -Name "preflight completed" -Passed ($preflightRaw.ExitCode -eq 0) -Detail ($(if ($preflightRaw.ExitCode -eq 0) { "ok" } else { $preflightRaw.Output }))

if ($StartGateway) {
    $resolvedOpenClawImage = Resolve-LocalDockerImageCandidate -PreferredImage $openClawImage -FallbackImages @(
        "ghcr.io/openclaw/openclaw:latest",
        "openclaw/openclaw:latest",
        "ghcr.io/openclaw/openclaw",
        "openclaw/openclaw"
    )

    if ($resolvedOpenClawImage.Exists -and ($resolvedOpenClawImage.Image -ne $openClawImage)) {
        Set-AimsDotEnvValues -Path $envPath -Values @{
            AIMS_OPENCLAW_IMAGE = $resolvedOpenClawImage.Image
        }
        $openClawImage = $resolvedOpenClawImage.Image
    }

    $gatewaySelection = Resolve-GatewaySelection -RequestedMode $GatewayMode -PortableRootPath $PortableRoot -DockerImage $openClawImage
    Add-Result -Name "configured openclaw image" -Passed $true -Detail $openClawImage
    Add-Result -Name "local openclaw image available" -Passed $resolvedOpenClawImage.Exists -Detail $(if ($resolvedOpenClawImage.Exists) { $resolvedOpenClawImage.Image } else { "missing locally" })
    Add-Result -Name "selected gateway mode" -Passed $gatewaySelection.Passed -Detail $gatewaySelection.Detail

    if (-not $gatewaySelection.Passed) {
        $results | Format-Table -AutoSize
        exit 1
    }

    $gatewayParams = @{
        StartServices  = $true
        CheckOllama    = $true
        TimeoutSeconds = $TimeoutSeconds
    }

    if ($IncludeInfra) {
        $gatewayParams["IncludeInfra"] = $true
    }

    if ($effectiveMode -eq "PrivateDocker") {
        $gatewayParams["UseLocalLlm"] = $true
    }

    if ($UseWsl) {
        $gatewayParams["UseWsl"] = $true
        if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
            $gatewayParams["WslDistro"] = $WslDistro
        }
    }

    if ($UseMirrorRegistry) {
        $gatewayParams["UseMirrorRegistry"] = $true
    }

    if ($gatewaySelection.Mode -eq "HostPortable") {
        $gatewayParams["HostGateway"] = $true
        $gatewayParams["ForceRestartHostGateway"] = $true
        $gatewayParams["PortableRoot"] = $PortableRoot
    }

    $gatewayRaw = Invoke-ScriptCapture -Path $gatewayHealthScript -Parameters $gatewayParams
    Add-Result -Name "gateway startup and health" -Passed ($gatewayRaw.ExitCode -eq 0) -Detail ($(if ($gatewayRaw.ExitCode -eq 0) { "ok" } else { $gatewayRaw.Output }))
}

$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
