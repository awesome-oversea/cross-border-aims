param(
    [string]$EnvPath,
    [string]$Endpoint,
    [string]$PrimaryModel,
    [string]$MultimodalModel,
    [switch]$RequireMultimodalModel,
    [switch]$ProbeGenerate,
    [switch]$AsJson,
    [int]$TimeoutSeconds = 10
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$envPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
$envMap = Read-AimsDotEnv -Path $envPath

$endpoint = if ($Endpoint) {
    $Endpoint
}
else {
    Get-AimsEnvValueOrDefault -Map $envMap -Key "LLM_OLLAMA_ENDPOINT" -Default "http://localhost:11434"
}

$primaryModel = if ($PrimaryModel) {
    $PrimaryModel
}
else {
    Get-AimsEnvValueOrDefault -Map $envMap -Key "LLM_PRIMARY_MODEL" -Default ""
}

$multimodalModel = if ($MultimodalModel) {
    $MultimodalModel
}
else {
    Get-AimsEnvValueOrDefault -Map $envMap -Key "LLM_MULTIMODAL_MODEL" -Default ""
}

$results = New-Object System.Collections.Generic.List[object]
$availableModels = @()
$listener = $null
$resolvedEndpoint = $endpoint

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

function Get-OllamaBaseUrl {
    param(
        [string]$RawEndpoint
    )

    $trimmed = $RawEndpoint.Trim().TrimEnd("/")
    $uri = [System.Uri]$trimmed
    $builder = [System.UriBuilder]::new($uri)

    if ($builder.Path -eq "/v1" -or $builder.Path -eq "v1") {
        $builder.Path = ""
    }

    return $builder.Uri.AbsoluteUri.TrimEnd("/")
}

function Get-OllamaListener {
    param(
        [System.Uri]$Uri
    )

    if ($Uri.Host -notin @("localhost", "127.0.0.1")) {
        return $null
    }

    $tcpCommand = Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue
    if ($null -eq $tcpCommand) {
        return $null
    }

    $connection = Get-NetTCPConnection -LocalPort $Uri.Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $connection) {
        return $null
    }

    $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
    [pscustomobject]@{
        Port        = $Uri.Port
        ProcessId   = $connection.OwningProcess
        ProcessName = if ($null -ne $process) { $process.ProcessName } else { "unknown" }
    }
}

function Invoke-OllamaJson {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body
    )

    $invokeArgs = @{
        Method      = $Method
        Uri         = $Url
        TimeoutSec  = $TimeoutSeconds
        ContentType = "application/json"
    }

    if ($null -ne $Body) {
        $invokeArgs["Body"] = ($Body | ConvertTo-Json -Depth 10 -Compress)
    }

    return Invoke-RestMethod @invokeArgs
}

if (-not (Test-Path -LiteralPath $envPath)) {
    throw ".env is missing. Run scripts/p0/Initialize-AimsEnv.ps1 first."
}

Add-Result -Name "LLM_OLLAMA_ENDPOINT configured" -Passed (-not [string]::IsNullOrWhiteSpace($endpoint)) -Detail $endpoint
Add-Result -Name "LLM_PRIMARY_MODEL configured" -Passed (-not [string]::IsNullOrWhiteSpace($primaryModel)) -Detail $(if ([string]::IsNullOrWhiteSpace($primaryModel)) { "missing" } else { $primaryModel })

if (-not [string]::IsNullOrWhiteSpace($multimodalModel)) {
    Add-Result -Name "LLM_MULTIMODAL_MODEL configured" -Passed $true -Detail $multimodalModel
}

if ($results | Where-Object { $_.Status -eq "FAIL" }) {
    if ($AsJson) {
        [pscustomobject]@{
            endpoint         = $endpoint
            resolvedEndpoint = $resolvedEndpoint
            primaryModel     = $primaryModel
            multimodalModel  = $multimodalModel
            availableModels  = @()
            listener         = $null
            results          = @($results)
        } | ConvertTo-Json -Depth 10
        exit 1
    }

    $results | Format-Table -AutoSize
    exit 1
}

try {
    $resolvedEndpoint = Get-OllamaBaseUrl -RawEndpoint $endpoint
    $uri = [System.Uri]$resolvedEndpoint
    $listener = Get-OllamaListener -Uri $uri

    if ($null -ne $listener) {
        Add-Result -Name "Ollama port listener" -Passed $true -Detail ("port {0} owned by pid {1} ({2})" -f $listener.Port, $listener.ProcessId, $listener.ProcessName)
    }
    elseif ($uri.Host -in @("localhost", "127.0.0.1")) {
        Add-Result -Name "Ollama port listener" -Passed $false -Detail ("no local listener found on port {0}" -f $uri.Port)
    }

    $tagsUrl = "{0}/api/tags" -f $resolvedEndpoint
    $tagsResponse = Invoke-OllamaJson -Method "GET" -Url $tagsUrl -Body $null
    $availableModels = @($tagsResponse.models | ForEach-Object { [string]$_.name } | Sort-Object -Unique)

    Add-Result -Name "Ollama endpoint reachable" -Passed $true -Detail $resolvedEndpoint
    Add-Result -Name "Ollama model list" -Passed ($availableModels.Count -gt 0) -Detail $(if ($availableModels.Count -gt 0) { $availableModels -join ", " } else { "no models returned" })
    Add-Result -Name "Primary model installed" -Passed ($primaryModel -in $availableModels) -Detail $primaryModel

    if (-not [string]::IsNullOrWhiteSpace($multimodalModel)) {
        $multimodalInstalled = ($multimodalModel -in $availableModels)
        $multimodalPassed = if ($RequireMultimodalModel) { $multimodalInstalled } else { $true }
        $multimodalDetail = if ($multimodalInstalled) { $multimodalModel } else { "$multimodalModel (optional, not installed)" }
        Add-Result -Name "Multimodal model installed" -Passed $multimodalPassed -Detail $multimodalDetail
    }

    if ($ProbeGenerate -and ($primaryModel -in $availableModels)) {
        $generateResponse = Invoke-OllamaJson -Method "POST" -Url ("{0}/api/generate" -f $resolvedEndpoint) -Body @{
            model  = $primaryModel
            prompt = "Reply with OK."
            stream = $false
        }

        $content = [string]$generateResponse.response
        Add-Result -Name "Primary model generate probe" -Passed (-not [string]::IsNullOrWhiteSpace($content)) -Detail $(if ([string]::IsNullOrWhiteSpace($content)) { "empty response" } else { $content.Trim() })
    }
}
catch {
    Add-Result -Name "Ollama endpoint reachable" -Passed $false -Detail $_.Exception.Message
}

if ($AsJson) {
    $jsonPayload = [ordered]@{
        endpoint         = [string]$endpoint
        resolvedEndpoint = [string]$resolvedEndpoint
        primaryModel     = [string]$primaryModel
        multimodalModel  = [string]$multimodalModel
        availableModels  = @($availableModels)
        listener         = if ($null -eq $listener) {
            $null
        }
        else {
            [pscustomobject]@{
                Port        = [int]$listener.Port
                ProcessId   = [int]$listener.ProcessId
                ProcessName = [string]$listener.ProcessName
            }
        }
        results          = @($results | ForEach-Object {
            [pscustomobject]@{
                Status = [string]$_.Status
                Name   = [string]$_.Name
                Detail = [string]$_.Detail
            }
        })
    }

    [pscustomobject]$jsonPayload | ConvertTo-Json -Depth 10
}
else {
    $results | Format-Table -AutoSize
}

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
