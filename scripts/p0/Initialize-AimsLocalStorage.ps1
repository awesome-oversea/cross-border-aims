param(
    [string]$EnvPath,
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$effectiveEnvPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }

if (-not (Test-Path -LiteralPath $effectiveEnvPath)) {
    throw ".env is missing. Run scripts/p0/Initialize-AimsEnv.ps1 first."
}

$envMap = Read-AimsDotEnv -Path $effectiveEnvPath
$toolsRoot = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_TOOLS_ROOT" -Default "D:/aitools"

function Normalize-AimsStoragePath {
    param(
        [string]$Path
    )

    return ([string]$Path).Trim().Replace("\", "/").TrimEnd("/")
}

function Test-AimsPathUnderRoot {
    param(
        [string]$Path,
        [string]$Root
    )

    $normalizedPath = (Normalize-AimsStoragePath -Path $Path).ToLowerInvariant()
    $normalizedRoot = (Normalize-AimsStoragePath -Path $Root).ToLowerInvariant()
    return ($normalizedPath -eq $normalizedRoot -or $normalizedPath.StartsWith($normalizedRoot + "/"))
}

$pathDefaults = [ordered]@{
    AIMS_TOOLS_ROOT             = "D:/aitools"
    AIMS_LOCAL_STORAGE_ROOT     = "D:/aitools/aims"
    AIMS_OLLAMA_DATA_DIR        = "D:/aitools/aims/ollama"
    AIMS_LOCAL_MODEL_CACHE_DIR  = "D:/aitools/aims/model-cache"
    AIMS_MYSQL_DATA_DIR         = "D:/aitools/aims/mysql"
    AIMS_REDIS_DATA_DIR         = "D:/aitools/aims/redis"
    AIMS_MINIO_DATA_DIR         = "D:/aitools/aims/minio"
    AIMS_MILVUS_DATA_DIR        = "D:/aitools/aims/milvus"
    AIMS_QDRANT_DATA_DIR        = "D:/aitools/aims/qdrant"
    AIMS_CLAWHUB_CACHE_DIR      = "D:/aitools/clawhub-cache"
    AIMS_NPM_CACHE_DIR          = "D:/aitools/npm-cache"
    AIMS_PIP_CACHE_DIR          = "D:/aitools/pip-cache"
}

$results = New-Object System.Collections.Generic.List[object]

foreach ($entry in $pathDefaults.GetEnumerator()) {
    $key = [string]$entry.Key
    $path = Get-AimsEnvValueOrDefault -Map $envMap -Key $key -Default ([string]$entry.Value)
    $underRoot = Test-AimsPathUnderRoot -Path $path -Root $toolsRoot
    $created = $false
    $exists = $false
    $detail = $path

    if ($underRoot) {
        if (-not (Test-Path -LiteralPath $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
            $created = $true
        }
        $exists = Test-Path -LiteralPath $path
    }
    else {
        $detail = "outside AIMS_TOOLS_ROOT=$toolsRoot; value=$path"
    }

    $results.Add([pscustomobject]@{
        Status    = if ($underRoot -and $exists) { "PASS" } else { "FAIL" }
        Name      = $key
        Path      = $path
        Created   = $created
        UnderRoot = $underRoot
        Detail    = $detail
    })
}

if ($AsJson) {
    [pscustomobject]@{
        envPath   = $effectiveEnvPath
        toolsRoot = $toolsRoot
        results   = @($results.ToArray())
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
