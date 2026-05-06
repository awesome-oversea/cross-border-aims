param(
    [string]$EnvPath
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$effectiveEnvPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
$composePath = Join-Path $repoRoot "docker-compose.yml"
$localLlmComposePath = Join-Path $repoRoot "docker-compose.local-llm.yml"
$envExamplePath = Join-Path $repoRoot ".env.example"
$ragDepsScript = Join-Path $repoRoot "scripts\p1\Install-AimsRagDependencies.ps1"
$marketSkillsScript = Join-Path $repoRoot "scripts\p0\Install-AimsMarketSkills.ps1"

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

function Read-TextOrEmpty {
    param(
        [string]$Path
    )

    if (Test-Path -LiteralPath $Path) {
        return Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    }

    return ""
}

$requiredPathKeys = @(
    "AIMS_TOOLS_ROOT",
    "AIMS_LOCAL_STORAGE_ROOT",
    "AIMS_OLLAMA_DATA_DIR",
    "AIMS_LOCAL_MODEL_CACHE_DIR",
    "AIMS_MYSQL_DATA_DIR",
    "AIMS_REDIS_DATA_DIR",
    "AIMS_MINIO_DATA_DIR",
    "AIMS_MILVUS_DATA_DIR",
    "AIMS_QDRANT_DATA_DIR",
    "AIMS_CLAWHUB_CACHE_DIR",
    "AIMS_NPM_CACHE_DIR",
    "AIMS_PIP_CACHE_DIR"
)

$envExampleText = Read-TextOrEmpty -Path $envExamplePath
$missingExampleKeys = @($requiredPathKeys | Where-Object { $envExampleText -notmatch "(?m)^$($_)=" })
Add-Result -Name ".env.example dependency path keys" -Passed ($missingExampleKeys.Count -eq 0) -Detail $(if ($missingExampleKeys.Count -eq 0) { "all present" } else { $missingExampleKeys -join ", " })

if (Test-Path -LiteralPath $effectiveEnvPath) {
    $envMap = Read-AimsDotEnv -Path $effectiveEnvPath
    $toolsRoot = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_TOOLS_ROOT" -Default "D:/aitools"
    $badPaths = New-Object System.Collections.Generic.List[string]

    foreach ($key in $requiredPathKeys) {
        $value = Get-AimsEnvValueOrDefault -Map $envMap -Key $key -Default ""
        $normalizedValue = ([string]$value).Replace("\", "/").TrimEnd("/")
        $normalizedRoot = ([string]$toolsRoot).Replace("\", "/").TrimEnd("/")
        if ([string]::IsNullOrWhiteSpace($value) -or -not ($normalizedValue -eq $normalizedRoot -or $normalizedValue.StartsWith($normalizedRoot + "/"))) {
            $badPaths.Add("$key=$value")
        }
    }

    Add-Result -Name ".env dependency paths under AIMS_TOOLS_ROOT" -Passed ($badPaths.Count -eq 0) -Detail $(if ($badPaths.Count -eq 0) { $toolsRoot } else { $badPaths -join "; " })
}
else {
    Add-Result -Name ".env dependency paths under AIMS_TOOLS_ROOT" -Passed $false -Detail ".env missing: $effectiveEnvPath"
}

$composeText = Read-TextOrEmpty -Path $composePath
$forbiddenProjectVolumes = @("./mysql-data", "./redis-data", "./milvus-data", "./minio-data", "./qdrant-data")
$foundForbiddenVolumes = @($forbiddenProjectVolumes | Where-Object { $composeText.Contains($_) })
Add-Result -Name "compose infra data volumes externalized" -Passed ($foundForbiddenVolumes.Count -eq 0) -Detail $(if ($foundForbiddenVolumes.Count -eq 0) { "no project-local infra data volumes" } else { $foundForbiddenVolumes -join ", " })

$localLlmComposeText = Read-TextOrEmpty -Path $localLlmComposePath
Add-Result -Name "local llm pip cache mounted" -Passed ($localLlmComposeText -match "AIMS_PIP_CACHE_DIR" -and $localLlmComposeText -match "/pip-cache") -Detail "cpu-model-cache-init should mount AIMS_PIP_CACHE_DIR"
Add-Result -Name "local llm avoids docker build dependency pulls" -Passed ($localLlmComposeText -notmatch "(?m)^\s*build:\s*$") -Detail "cpu-model-cache-init should use a local image with pull_policy never"
Add-Result -Name "local llm python image pull disabled" -Passed ($localLlmComposeText -match "AIMS_PYTHON_IMAGE" -and $localLlmComposeText -match "pull_policy:\s+never") -Detail "python image must be preloaded or explicitly pulled once"

$ragDepsText = Read-TextOrEmpty -Path $ragDepsScript
Add-Result -Name "rag pip install uses D:/aitools cache" -Passed ($ragDepsText -match "AIMS_PIP_CACHE_DIR" -and $ragDepsText -match "--cache-dir") -Detail $ragDepsScript

$marketSkillsText = Read-TextOrEmpty -Path $marketSkillsScript
Add-Result -Name "market skill npx uses D:/aitools cache" -Passed ($marketSkillsText -match "AIMS_NPM_CACHE_DIR" -and $marketSkillsText -match "npm_config_cache" -and $marketSkillsText -match "AIMS_CLAWHUB_CACHE_DIR") -Detail $marketSkillsScript

$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
