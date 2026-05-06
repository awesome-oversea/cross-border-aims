param(
    [string]$Distro,
    [string]$EnvPath,
    [string]$WslToolsRoot = "/mnt/d/aitools",
    [switch]$IncludeInfra,
    [switch]$UseLocalLlm,
    [switch]$StartGateway,
    [switch]$PullModels,
    [switch]$WarmModelCaches,
    [switch]$DryRun,
    [string[]]$Services
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$sourceEnvPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
$generatedDir = Join-Path $repoRoot ".generated"
$wslEnvPath = Join-Path $generatedDir ".env.wsl"

if (-not (Test-Path -LiteralPath $sourceEnvPath)) {
    throw ".env is missing. Run scripts/p0/Initialize-AimsEnv.ps1 first."
}

if (-not (Test-Path -LiteralPath $generatedDir)) {
    New-Item -ItemType Directory -Path $generatedDir -Force | Out-Null
}

& (Join-Path $PSScriptRoot "Initialize-AimsLocalStorage.ps1") -EnvPath $sourceEnvPath -AsJson | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Local storage initialization failed."
}

Copy-Item -LiteralPath $sourceEnvPath -Destination $wslEnvPath -Force

$wslRoot = $WslToolsRoot.TrimEnd("/")
$wslAimsRoot = "$wslRoot/aims"
$wslValues = @{
    AIMS_TOOLS_ROOT            = $wslRoot
    AIMS_LOCAL_STORAGE_ROOT    = $wslAimsRoot
    AIMS_OLLAMA_DATA_DIR       = "$wslAimsRoot/ollama"
    AIMS_LOCAL_MODEL_CACHE_DIR = "$wslAimsRoot/model-cache"
    AIMS_MYSQL_DATA_DIR        = "$wslAimsRoot/mysql"
    AIMS_REDIS_DATA_DIR        = "$wslAimsRoot/redis"
    AIMS_MINIO_DATA_DIR        = "$wslAimsRoot/minio"
    AIMS_MILVUS_DATA_DIR       = "$wslAimsRoot/milvus"
    AIMS_QDRANT_DATA_DIR       = "$wslAimsRoot/qdrant"
    AIMS_CLAWHUB_CACHE_DIR     = "$wslRoot/clawhub-cache"
    AIMS_NPM_CACHE_DIR         = "$wslRoot/npm-cache"
    AIMS_PIP_CACHE_DIR         = "$wslRoot/pip-cache"
}

if ($UseLocalLlm) {
    $wslValues["AIMS_DOCKER_OLLAMA_ENDPOINT"] = "http://ollama:11434"
}

Set-AimsDotEnvValues -Path $wslEnvPath -Values $wslValues

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

function ConvertTo-WslPathFallback {
    param(
        [string]$WindowsPath
    )

    $normalized = ([string]$WindowsPath).Replace("\", "/")
    if ($normalized -match "^([A-Za-z]):/(.*)$") {
        return "/mnt/" + $matches[1].ToLowerInvariant() + "/" + $matches[2]
    }

    return $normalized
}

$wslBaseArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Distro)) {
    $wslBaseArgs += @("-d", $Distro)
}

$repoWslPath = ""
if ($DryRun) {
    $repoWslPath = ConvertTo-WslPathFallback -WindowsPath $repoRoot
}
else {
    $repoWslPathOutput = & wsl.exe @wslBaseArgs wslpath -a $repoRoot 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("Failed to translate repo path through WSL: " + ($repoWslPathOutput | Out-String).Trim())
    }
    $repoWslPath = ($repoWslPathOutput | Select-Object -First 1).Trim()
}

$composeOptions = @("--env-file", ".generated/.env.wsl", "-f", "docker-compose.yml")
if ($UseLocalLlm) {
    $composeOptions += @("-f", "docker-compose.local-llm.yml")
}

$targetServices = New-Object System.Collections.Generic.List[string]
if ($Services -and $Services.Count -gt 0) {
    foreach ($service in $Services) {
        if (-not [string]::IsNullOrWhiteSpace($service)) {
            $targetServices.Add($service)
        }
    }
}
else {
    if ($IncludeInfra) {
        foreach ($service in @("mysql", "redis", "etcd", "minio", "milvus", "qdrant")) {
            $targetServices.Add($service)
        }
    }
    if ($UseLocalLlm) {
        $targetServices.Add("ollama")
    }
    if ($StartGateway -or $targetServices.Count -eq 0) {
        $targetServices.Add("openclaw")
    }
}

$storageDirs = @(
    $wslRoot,
    $wslAimsRoot,
    "$wslAimsRoot/ollama",
    "$wslAimsRoot/model-cache",
    "$wslAimsRoot/mysql",
    "$wslAimsRoot/redis",
    "$wslAimsRoot/minio",
    "$wslAimsRoot/milvus",
    "$wslAimsRoot/qdrant",
    "$wslRoot/clawhub-cache",
    "$wslRoot/npm-cache",
    "$wslRoot/pip-cache"
)

$composePrefix = "docker compose " + (Join-BashArguments -Values $composeOptions)
$commands = New-Object System.Collections.Generic.List[string]
$commands.Add("mkdir -p " + (Join-BashArguments -Values $storageDirs))
$commands.Add("cd " + (ConvertTo-BashLiteral -Value $repoWslPath))
$commands.Add("export NPM_CONFIG_CACHE=" + (ConvertTo-BashLiteral -Value "$wslRoot/npm-cache") + " npm_config_cache=" + (ConvertTo-BashLiteral -Value "$wslRoot/npm-cache") + " PIP_CACHE_DIR=" + (ConvertTo-BashLiteral -Value "$wslRoot/pip-cache") + " CLAWHUB_CACHE_DIR=" + (ConvertTo-BashLiteral -Value "$wslRoot/clawhub-cache"))
$commands.Add($composePrefix + " up --pull never -d " + (Join-BashArguments -Values $targetServices.ToArray()))

if ($PullModels) {
    if (-not $UseLocalLlm) {
        throw "-PullModels requires -UseLocalLlm."
    }
    $commands.Add($composePrefix + " run --rm ollama-model-init")
}

if ($WarmModelCaches) {
    if (-not $UseLocalLlm) {
        throw "-WarmModelCaches requires -UseLocalLlm."
    }
    $commands.Add($composePrefix + " run --rm cpu-model-cache-init")
}

$bashCommand = ($commands -join " && ")
Write-Host "WSL env written to $wslEnvPath"
Write-Host ("Running in WSL path: " + $repoWslPath)
Write-Host ("Services: " + ($targetServices.ToArray() -join ", "))

if ($DryRun) {
    Write-Host "Dry run command:"
    Write-Host $bashCommand
    exit 0
}

& wsl.exe @wslBaseArgs bash -lc $bashCommand
exit $LASTEXITCODE
