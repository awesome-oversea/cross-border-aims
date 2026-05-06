param(
    [switch]$StartServices,
    [switch]$IncludeInfra,
    [switch]$UseMirrorRegistry,
    [switch]$UseLocalLlm,
    [switch]$UseWsl,
    [string]$WslDistro,
    [switch]$HostGateway,
    [switch]$ForceRestartHostGateway,
    [switch]$CheckOllama,
    [string]$PortableRoot = "D:\openclaw\openclaw-portable-win-x64",
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$composeFiles = Resolve-AimsComposeFiles -RepoRoot $repoRoot -UseMirrorRegistry:$UseMirrorRegistry -UseLocalLlm:$UseLocalLlm
$envPath = Join-Path $repoRoot ".env"
$runtimeConfigScript = Join-Path $PSScriptRoot "Export-AimsRuntimeConfig.ps1"
$runtimeConfigPath = Join-Path $repoRoot ".generated/openclaw.runtime.json"
$hostGatewayScript = Join-Path $PSScriptRoot "Start-AimsGatewayHost.ps1"
$hostCliScript = Join-Path $PSScriptRoot "Invoke-AimsOpenClawHostCli.ps1"
$ollamaCheckScript = Join-Path $PSScriptRoot "Invoke-AimsOllamaCheck.ps1"
$localLlmHealthScript = Join-Path $PSScriptRoot "Invoke-AimsLocalLlmHealth.ps1"
$localStorageScript = Join-Path $PSScriptRoot "Initialize-AimsLocalStorage.ps1"
$wslComposeScript = Join-Path $PSScriptRoot "Start-AimsWslCompose.ps1"
$envMap = Read-AimsDotEnv -Path $envPath
$gatewayPort = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_GATEWAY_PORT" -Default "18789"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw ".env is missing. Run scripts/p0/Initialize-AimsEnv.ps1 first."
}

if ([string]::IsNullOrWhiteSpace($envMap["AIMS_GATEWAY_TOKEN"])) {
    throw "AIMS_GATEWAY_TOKEN is missing. Re-run scripts/p0/Initialize-AimsEnv.ps1 -Force."
}

& $localStorageScript -EnvPath $envPath -AsJson | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "AIMS local storage initialization failed."
}

$results = New-Object System.Collections.Generic.List[object]
$script:RepoWslPath = $null
$script:WslComposePrepared = $false

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

function Get-WslBaseArguments {
    $args = @()
    if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
        $args += @("-d", $WslDistro)
    }

    return ,$args
}

function Get-RepoWslPath {
    if (-not [string]::IsNullOrWhiteSpace($script:RepoWslPath)) {
        return $script:RepoWslPath
    }

    $wslBaseArgs = Get-WslBaseArguments
    $repoWslPathOutput = & wsl.exe @wslBaseArgs wslpath -a $repoRoot 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("Failed to translate repo path through WSL: " + ($repoWslPathOutput | Out-String).Trim())
    }

    $script:RepoWslPath = ($repoWslPathOutput | Select-Object -First 1).Trim()
    return $script:RepoWslPath
}

function Ensure-WslComposeContext {
    if ($script:WslComposePrepared) {
        return
    }

    if (-not (Test-Path -LiteralPath $wslComposeScript)) {
        throw "WSL compose script is missing: $wslComposeScript"
    }

    $dryRunParams = @{
        DryRun       = $true
        StartGateway = $true
    }

    if ($UseLocalLlm) {
        $dryRunParams["UseLocalLlm"] = $true
    }

    if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
        $dryRunParams["Distro"] = $WslDistro
    }

    $dryRunOutput = & $wslComposeScript @dryRunParams 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("Failed to prepare WSL compose context: " + ($dryRunOutput | Out-String).Trim())
    }

    $script:WslComposePrepared = $true
}

function Invoke-WslCompose {
    param(
        [string[]]$ComposeArgs
    )

    try {
        Ensure-WslComposeContext
        $repoWslPath = Get-RepoWslPath
        $composeOptions = New-Object System.Collections.Generic.List[string]
        $composeOptions.Add("--env-file")
        $composeOptions.Add(".generated/.env.wsl")

        foreach ($composeFile in $composeFiles) {
            $composeOptions.Add("-f")
            $composeOptions.Add((Split-Path -Leaf $composeFile))
        }

        foreach ($arg in $ComposeArgs) {
            $composeOptions.Add($arg)
        }

        $bashCommand = "cd " + (ConvertTo-BashLiteral -Value $repoWslPath) + " && docker compose " + (Join-BashArguments -Values $composeOptions.ToArray())
        $wslBaseArgs = Get-WslBaseArguments
        $output = & wsl.exe @wslBaseArgs bash -lc $bashCommand 2>&1

        return [pscustomobject]@{
            ExitCode = $LASTEXITCODE
            Output   = ($output | Out-String).Trim()
        }
    }
    catch {
        return [pscustomobject]@{
            ExitCode = 1
            Output   = $_.Exception.Message
        }
    }
}

function Invoke-Compose {
    param(
        [string[]]$ComposeArgs,
        [int]$TimeoutSeconds = 120
    )

    if ($UseWsl) {
        return Invoke-WslCompose -ComposeArgs $ComposeArgs
    }

    $composeCommand = New-AimsComposeCommandArguments -ComposeFiles $composeFiles -AdditionalArgs $ComposeArgs
    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process -FilePath "docker.exe" -ArgumentList $composeCommand -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $exited = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $exited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            return [pscustomobject]@{
                ExitCode = 124
                Output   = ("Timed out after {0}s: docker.exe {1}" -f $TimeoutSeconds, ($composeCommand -join " "))
            }
        }

        $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { "" }
        $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { "" }
        $output = @($stdout, $stderr) -join [System.Environment]::NewLine
        $exitCode = $process.ExitCode
    }
    finally {
        Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output   = $output.Trim()
    }
}

function Invoke-HostOpenClaw {
    param(
        [string[]]$CliArgs
    )

    $output = & $hostCliScript -PortableRoot $PortableRoot -EnvPath $envPath -OpenClawArgs $CliArgs 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output   = ($output | Out-String).Trim()
    }
}

function Wait-HttpEndpoint {
    param(
        [string]$Url,
        [int]$Seconds
    )

    $detail = "no response"
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return [pscustomobject]@{
                    Passed = $true
                    Detail = "HTTP $($response.StatusCode)"
                }
            }
        }
        catch {
            $detail = $_.Exception.Message
        }

        Start-Sleep -Seconds 5
    }
    while ((Get-Date) -lt $deadline)

    return [pscustomobject]@{
        Passed = $false
        Detail = $detail
    }
}

& $runtimeConfigScript -EnvPath $envPath -OutputPath $runtimeConfigPath -Activate | Out-Host
Add-Result -Name "runtime config exported" -Passed (Test-Path -LiteralPath $runtimeConfigPath) -Detail $runtimeConfigPath

if ($UseWsl -and $HostGateway) {
    Add-Result -Name "gateway runtime mode" -Passed $false -Detail "-UseWsl does not support -HostGateway. Use the Dockerized OpenClaw gateway path instead."
    $results | Format-Table -AutoSize
    exit 1
}

if ($StartServices) {
    if ($UseWsl) {
        if (-not (Test-Path -LiteralPath $wslComposeScript)) {
            Add-Result -Name "wsl compose script exists" -Passed $false -Detail $wslComposeScript
        }
        else {
            $wslStartParams = @{
                StartGateway = $true
            }

            if ($IncludeInfra) {
                $wslStartParams["IncludeInfra"] = $true
            }

            if ($UseLocalLlm) {
                $wslStartParams["UseLocalLlm"] = $true
            }

            if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
                $wslStartParams["Distro"] = $WslDistro
            }

            $wslStartRaw = & $wslComposeScript @wslStartParams 2>&1
            $wslStartText = ($wslStartRaw | Out-String).Trim()
            Add-Result -Name "wsl compose up stack" -Passed ($LASTEXITCODE -eq 0) -Detail $(if ([string]::IsNullOrWhiteSpace($wslStartText)) { "started" } else { $wslStartText })
            if ($LASTEXITCODE -eq 0) {
                $script:WslComposePrepared = $true
            }
        }
    }
    else {
        if ($IncludeInfra) {
            $infraServices = @("mysql", "redis", "etcd", "minio", "milvus", "qdrant")
            $infraUp = Invoke-Compose -ComposeArgs (@("up", "--pull", "never", "-d") + $infraServices)
            Add-Result -Name "docker compose up infra" -Passed ($infraUp.ExitCode -eq 0) -Detail ($(if ($infraUp.Output) { $infraUp.Output } else { "started" }))
        }

        if ($UseLocalLlm) {
            $localLlmUp = Invoke-Compose -ComposeArgs @("up", "--pull", "never", "-d", "ollama")
            Add-Result -Name "docker compose up local llm" -Passed ($localLlmUp.ExitCode -eq 0) -Detail ($(if ($localLlmUp.Output) { $localLlmUp.Output } else { "started" }))
        }

        if ($HostGateway) {
            & $hostGatewayScript -PortableRoot $PortableRoot -EnvPath $envPath -ForceRestart:$ForceRestartHostGateway
            Add-Result -Name "start host gateway" -Passed ($LASTEXITCODE -eq 0) -Detail ("portable root: " + $PortableRoot)
        }
        else {
            $up = Invoke-Compose -ComposeArgs @("up", "--pull", "never", "-d", "openclaw")
            Add-Result -Name "docker compose up gateway" -Passed ($up.ExitCode -eq 0) -Detail ($(if ($up.Output) { $up.Output } else { "started" }))
        }
    }

    $startupFailures = @($results | Where-Object {
        $_.Status -eq "FAIL" -and $_.Name -in @("docker compose up infra", "docker compose up local llm", "start host gateway", "docker compose up gateway", "wsl compose script exists", "wsl compose up stack")
    })
    if ($startupFailures.Count -gt 0) {
        $results | Format-Table -AutoSize
        exit 1
    }
}

$healthz = Wait-HttpEndpoint -Url ("http://127.0.0.1:{0}/healthz" -f $gatewayPort) -Seconds $TimeoutSeconds
Add-Result -Name "gateway healthz" -Passed $healthz.Passed -Detail $healthz.Detail

$readyz = Wait-HttpEndpoint -Url ("http://127.0.0.1:{0}/readyz" -f $gatewayPort) -Seconds $TimeoutSeconds
Add-Result -Name "gateway readyz" -Passed $readyz.Passed -Detail $readyz.Detail

$deepHealth = if ($HostGateway) {
    Invoke-HostOpenClaw -CliArgs @("gateway", "health", "--url", ("ws://127.0.0.1:{0}" -f $gatewayPort), "--token", $envMap["AIMS_GATEWAY_TOKEN"], "--json")
}
elseif ($UseWsl) {
    Invoke-WslCompose -ComposeArgs @("exec", "-T", "openclaw", "openclaw", "gateway", "health", "--url", ("ws://127.0.0.1:{0}" -f $gatewayPort), "--token", $envMap["AIMS_GATEWAY_TOKEN"], "--json")
}
else {
    Invoke-Compose -ComposeArgs @("exec", "-T", "openclaw", "openclaw", "gateway", "health", "--url", ("ws://127.0.0.1:{0}" -f $gatewayPort), "--token", $envMap["AIMS_GATEWAY_TOKEN"], "--json")
}
Add-Result -Name "gateway deep health" -Passed ($deepHealth.ExitCode -eq 0) -Detail $deepHealth.Output

$rpcProbe = if ($HostGateway) {
    Invoke-HostOpenClaw -CliArgs @("gateway", "probe", "--url", ("ws://127.0.0.1:{0}" -f $gatewayPort), "--token", $envMap["AIMS_GATEWAY_TOKEN"], "--json")
}
elseif ($UseWsl) {
    Invoke-WslCompose -ComposeArgs @("exec", "-T", "openclaw", "openclaw", "gateway", "probe", "--url", ("ws://127.0.0.1:{0}" -f $gatewayPort), "--token", $envMap["AIMS_GATEWAY_TOKEN"], "--json")
}
else {
    Invoke-Compose -ComposeArgs @("exec", "-T", "openclaw", "openclaw", "gateway", "probe", "--url", ("ws://127.0.0.1:{0}" -f $gatewayPort), "--token", $envMap["AIMS_GATEWAY_TOKEN"], "--json")
}
Add-Result -Name "gateway RPC probe" -Passed ($rpcProbe.ExitCode -eq 0) -Detail $rpcProbe.Output

if ($CheckOllama) {
    if ($UseLocalLlm) {
        if (-not (Test-Path -LiteralPath $localLlmHealthScript)) {
            Add-Result -Name "local llm health script exists" -Passed $false -Detail $localLlmHealthScript
        }
        else {
            $localLlmCheckParams = @{
                AsJson         = $true
                TimeoutSeconds = 15
            }
            if ($UseWsl) {
                $localLlmCheckParams["UseWsl"] = $true
                if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
                    $localLlmCheckParams["WslDistro"] = $WslDistro
                }
            }

            $localLlmCheckRaw = & $localLlmHealthScript @localLlmCheckParams 2>&1
            $localLlmCheckText = ($localLlmCheckRaw | Out-String).Trim()
            $localLlmJsonStart = $localLlmCheckText.IndexOf("{")

            if ($localLlmJsonStart -lt 0) {
                Add-Result -Name "local llm check output" -Passed $false -Detail $localLlmCheckText
            }
            else {
                $localLlmCheck = $localLlmCheckText.Substring($localLlmJsonStart) | ConvertFrom-Json
                foreach ($item in @($localLlmCheck.results)) {
                    Add-Result -Name ("local llm: " + $item.Name) -Passed ($item.Status -eq "PASS") -Detail ([string]$item.Detail)
                }
            }
        }
    }
    elseif (-not (Test-Path -LiteralPath $ollamaCheckScript)) {
        Add-Result -Name "ollama check script exists" -Passed $false -Detail $ollamaCheckScript
    }
    else {
        $ollamaCheckRaw = & $ollamaCheckScript -EnvPath $envPath -AsJson 2>&1
        $ollamaCheckText = ($ollamaCheckRaw | Out-String).Trim()
        $ollamaJsonStart = $ollamaCheckText.IndexOf("{")

        if ($ollamaJsonStart -lt 0) {
            Add-Result -Name "ollama check output" -Passed $false -Detail $ollamaCheckText
        }
        else {
            $ollamaCheck = $ollamaCheckText.Substring($ollamaJsonStart) | ConvertFrom-Json
            foreach ($item in @($ollamaCheck.results)) {
                Add-Result -Name ("ollama: " + $item.Name) -Passed ($item.Status -eq "PASS") -Detail ([string]$item.Detail)
            }
        }
    }
}

$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
