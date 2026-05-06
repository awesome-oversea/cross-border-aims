param(
    [switch]$StartServices,
    [switch]$PullModels,
    [switch]$WarmModelCaches,
    [switch]$ProbeGenerate,
    [switch]$UseWsl,
    [string]$WslDistro,
    [switch]$AsJson,
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$composePath = Get-AimsLocalLlmComposePath -RepoRoot $repoRoot
$envPath = Join-Path $repoRoot ".env"
$ollamaCheckScript = Join-Path $PSScriptRoot "Invoke-AimsOllamaCheck.ps1"
$localStorageScript = Join-Path $PSScriptRoot "Initialize-AimsLocalStorage.ps1"
$wslComposeScript = Join-Path $PSScriptRoot "Start-AimsWslCompose.ps1"

if (-not (Test-Path -LiteralPath $composePath)) {
    throw "Local LLM compose file is missing: $composePath"
}

if (-not (Test-Path -LiteralPath $envPath)) {
    throw ".env is missing. Run scripts/p0/Initialize-AimsEnv.ps1 first."
}

$envMap = Read-AimsDotEnv -Path $envPath

& $localStorageScript -EnvPath $envPath -AsJson | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "AIMS local storage initialization failed."
}

$ollamaDataDir = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_OLLAMA_DATA_DIR" -Default "D:/aitools/aims/ollama"
$modelCacheDir = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_LOCAL_MODEL_CACHE_DIR" -Default "D:/aitools/aims/model-cache"
$dockerEndpoint = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_DOCKER_OLLAMA_ENDPOINT" -Default "http://ollama:11434"
$hostPort = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_OLLAMA_HOST_PORT" -Default "11435"
$sharedHostEndpoint = Get-AimsEnvValueOrDefault -Map $envMap -Key "LLM_OLLAMA_ENDPOINT" -Default "http://localhost:11434"
$dockerPublishedEndpoint = "http://localhost:{0}" -f $hostPort
$primaryModel = Get-AimsEnvValueOrDefault -Map $envMap -Key "LLM_PRIMARY_MODEL" -Default ""
$multimodalModel = Get-AimsEnvValueOrDefault -Map $envMap -Key "LLM_MULTIMODAL_MODEL" -Default ""

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

function Ensure-Directory {
    param(
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Invoke-Compose {
    param(
        [string[]]$ComposeArgs,
        [int]$TimeoutSeconds = 120
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()
    $dockerArgs = @("compose", "-f", $composePath) + $ComposeArgs

    try {
        $process = Start-Process -FilePath "docker.exe" -ArgumentList $dockerArgs -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $exited = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $exited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            return [pscustomobject]@{
                ExitCode = 124
                Output   = ("Timed out after {0}s: docker.exe {1}" -f $TimeoutSeconds, ($dockerArgs -join " "))
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

Add-Result -Name "local llm compose exists" -Passed $true -Detail $composePath
Add-Result -Name "docker ollama endpoint" -Passed (-not [string]::IsNullOrWhiteSpace($dockerEndpoint)) -Detail $dockerEndpoint
Add-Result -Name "shared host ollama endpoint" -Passed (-not [string]::IsNullOrWhiteSpace($sharedHostEndpoint)) -Detail $sharedHostEndpoint
Add-Result -Name "docker published ollama endpoint" -Passed (-not [string]::IsNullOrWhiteSpace($dockerPublishedEndpoint)) -Detail $dockerPublishedEndpoint

Ensure-Directory -Path $ollamaDataDir
Ensure-Directory -Path $modelCacheDir
Add-Result -Name "ollama data dir" -Passed (Test-Path -LiteralPath $ollamaDataDir) -Detail $ollamaDataDir
Add-Result -Name "local model cache dir" -Passed (Test-Path -LiteralPath $modelCacheDir) -Detail $modelCacheDir

$startupRequested = ($StartServices -or $PullModels -or $WarmModelCaches)

if ($startupRequested) {
    if ($UseWsl) {
        if (-not (Test-Path -LiteralPath $wslComposeScript)) {
            Add-Result -Name "wsl compose script exists" -Passed $false -Detail $wslComposeScript
        }
        else {
            $wslParams = @{
                UseLocalLlm = $true
            }

            if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
                $wslParams["Distro"] = $WslDistro
            }

            if ($PullModels) {
                $wslParams["PullModels"] = $true
            }

            if ($WarmModelCaches) {
                $wslParams["WarmModelCaches"] = $true
            }

            $wslRaw = & $wslComposeScript @wslParams 2>&1
            $wslText = ($wslRaw | Out-String).Trim()
            Add-Result -Name "wsl compose bootstrap local llm" -Passed ($LASTEXITCODE -eq 0) -Detail $(if ([string]::IsNullOrWhiteSpace($wslText)) { "completed" } else { $wslText })
        }
    }
    else {
        if ($StartServices) {
            $up = Invoke-Compose -ComposeArgs @("up", "--pull", "never", "-d", "ollama")
            Add-Result -Name "docker compose up ollama" -Passed ($up.ExitCode -eq 0) -Detail $(if ($up.Output) { $up.Output } else { "started" })
        }

        if ($PullModels) {
            $pull = Invoke-Compose -ComposeArgs @("run", "--rm", "ollama-model-init")
            Add-Result -Name "docker compose pull ollama models" -Passed ($pull.ExitCode -eq 0) -Detail $(if ($pull.Output) { $pull.Output } else { "completed" })
        }

        if ($WarmModelCaches) {
            $warm = Invoke-Compose -ComposeArgs @("run", "--rm", "cpu-model-cache-init")
            Add-Result -Name "docker compose warm cpu model cache" -Passed ($warm.ExitCode -eq 0) -Detail $(if ($warm.Output) { $warm.Output } else { "completed" })
        }
    }
}

$tagsUrl = "{0}/api/tags" -f ($dockerPublishedEndpoint.TrimEnd("/"))
$hostProbe = Wait-HttpEndpoint -Url $tagsUrl -Seconds $TimeoutSeconds
Add-Result -Name "docker-published ollama tags endpoint" -Passed $hostProbe.Passed -Detail $hostProbe.Detail

if (-not (Test-Path -LiteralPath $ollamaCheckScript)) {
    Add-Result -Name "ollama check script exists" -Passed $false -Detail $ollamaCheckScript
}
else {
    if ($ProbeGenerate) {
        $ollamaCheckRaw = & $ollamaCheckScript -EnvPath $envPath -Endpoint $dockerPublishedEndpoint -PrimaryModel $primaryModel -MultimodalModel $multimodalModel -AsJson -ProbeGenerate 2>&1
    }
    else {
        $ollamaCheckRaw = & $ollamaCheckScript -EnvPath $envPath -Endpoint $dockerPublishedEndpoint -PrimaryModel $primaryModel -MultimodalModel $multimodalModel -AsJson 2>&1
    }

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

if ($AsJson) {
    [pscustomobject]@{
        dockerEndpoint          = [string]$dockerEndpoint
        sharedHostEndpoint      = [string]$sharedHostEndpoint
        dockerPublishedEndpoint = [string]$dockerPublishedEndpoint
        primaryModel            = [string]$primaryModel
        multimodalModel         = [string]$multimodalModel
        results                 = @($results | ForEach-Object {
            [pscustomobject]@{
                Status = [string]$_.Status
                Name   = [string]$_.Name
                Detail = [string]$_.Detail
            }
        })
    } | ConvertTo-Json -Depth 10
}
else {
    $results | Format-Table -AutoSize
}

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
