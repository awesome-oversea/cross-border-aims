param(
    [switch]$Force,
    [switch]$SkipRuntimeConfig
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$envExamplePath = Join-Path $repoRoot ".env.example"
$envPath = Join-Path $repoRoot ".env"
$runtimeConfigPath = Join-Path $repoRoot ".generated/openclaw.runtime.json"
$runtimeConfigScript = Join-Path $PSScriptRoot "Export-AimsRuntimeConfig.ps1"
$localStorageScript = Join-Path $PSScriptRoot "Initialize-AimsLocalStorage.ps1"

if (-not (Test-Path -LiteralPath $envExamplePath)) {
    throw ".env.example not found: $envExamplePath"
}

if ((Test-Path -LiteralPath $envPath) -and -not $Force) {
    throw ".env already exists. Use -Force to overwrite it."
}

Copy-Item -LiteralPath $envExamplePath -Destination $envPath -Force

Set-AimsDotEnvValues -Path $envPath -Values @{
    AIMS_GATEWAY_TOKEN        = (New-AimsHexSecret -ByteCount 32)
    AIMS_OPENCLAW_CONFIG_PATH = "./.generated/openclaw.runtime.json"
    AIMS_OPENCLAW_IMAGE       = "ghcr.io/openclaw/openclaw:latest"
    AIMS_OLLAMA_IMAGE         = "ollama/ollama:latest"
    AIMS_PYTHON_IMAGE         = "python:3.11-slim"
    AIMS_DOCKER_OLLAMA_ENDPOINT = "http://ollama:11434"
    AIMS_HOST_SHARED_OLLAMA_ENDPOINT = "http://host.docker.internal:11434"
    AIMS_OLLAMA_HOST_PORT     = "11435"
    AIMS_TOOLS_ROOT           = "D:/aitools"
    AIMS_LOCAL_STORAGE_ROOT   = "D:/aitools/aims"
    AIMS_OLLAMA_DATA_DIR      = "D:/aitools/aims/ollama"
    AIMS_LOCAL_MODEL_CACHE_DIR = "D:/aitools/aims/model-cache"
    AIMS_MYSQL_DATA_DIR       = "D:/aitools/aims/mysql"
    AIMS_REDIS_DATA_DIR       = "D:/aitools/aims/redis"
    AIMS_MINIO_DATA_DIR       = "D:/aitools/aims/minio"
    AIMS_MILVUS_DATA_DIR      = "D:/aitools/aims/milvus"
    AIMS_QDRANT_DATA_DIR      = "D:/aitools/aims/qdrant"
    AIMS_CLAWHUB_CACHE_DIR    = "D:/aitools/clawhub-cache"
    AIMS_NPM_CACHE_DIR        = "D:/aitools/npm-cache"
    AIMS_PIP_CACHE_DIR        = "D:/aitools/pip-cache"
    AIMS_LOCAL_MODEL_PULL_LIST = "qwen2.5:1.5b-instruct"
    AIMS_LOCAL_OPTIONAL_MODEL_PULL_LIST = "qwen3.5:2b-q8_0"
    AIMS_LOCAL_RERANK_REPO    = "BAAI/bge-reranker-base"
    AIMS_LOCAL_WHISPER_REPO   = "openai/whisper-tiny"
    OLLAMA_API_KEY            = "ollama-local"
    LLM_PRIMARY_MODEL         = "qwen2.5:1.5b-instruct"
    LLM_VLLM_ENDPOINT         = "http://localhost:8000/v1"
    LLM_TRITON_ENDPOINT       = "http://localhost:8000"
    LLM_OLLAMA_ENDPOINT       = "http://localhost:11434"
    LLM_MULTIMODAL_MODEL      = "qwen3.5:2b-q8_0"
    LLM_RERANK_MODEL          = "bge-reranker-base"
    DEEPSEEK_API_KEY          = ""
    MOONSHOT_API_KEY          = ""
    ZHIPU_API_KEY             = ""
    MYSQL_ROOT_PASSWORD       = (New-AimsAlphaNumericSecret -Length 24)
    MYSQL_PASSWORD            = (New-AimsAlphaNumericSecret -Length 24)
    MINIO_ROOT_USER           = "aimsminio"
    MINIO_ROOT_PASSWORD       = (New-AimsAlphaNumericSecret -Length 24)
}

& $localStorageScript -EnvPath $envPath | Out-Host

if (-not $SkipRuntimeConfig) {
    & $runtimeConfigScript -EnvPath $envPath -OutputPath $runtimeConfigPath -Activate | Out-Host
}

Write-Host ".env initialized at $envPath"
Write-Host "Generated local runtime secrets: AIMS_GATEWAY_TOKEN, MYSQL_ROOT_PASSWORD, MYSQL_PASSWORD, MINIO_ROOT_PASSWORD."
Write-Host "Seeded optional local Ollama defaults via OLLAMA_API_KEY and LLM_* settings."
Write-Host "Cloud providers remain available after you fill DEEPSEEK_API_KEY, MOONSHOT_API_KEY, or ZHIPU_API_KEY."
Write-Host "Prepared Docker/WSL-friendly storage defaults under D:/aitools for model, cache, and infra data."
Write-Host "Fill in the remaining provider and channel credentials before enabling the corresponding integrations."
