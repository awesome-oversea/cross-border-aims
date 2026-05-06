param(
    [string]$PythonPath = ".\.venv\Scripts\python.exe",
    [string]$EnvPath,
    [switch]$UpgradePip,
    [switch]$IncludeSentenceTransformers
)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "p0\Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$effectiveEnvPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
$requirementsPath = Join-Path $PSScriptRoot "requirements-aims-rag.txt"
$embedRequirementsPath = Join-Path $PSScriptRoot "requirements-aims-rag-embed.txt"
$pythonExecutable = if ([System.IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $repoRoot $PythonPath }
$envMap = Read-AimsDotEnv -Path $effectiveEnvPath
$pipCacheDir = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_PIP_CACHE_DIR" -Default "D:/aitools/pip-cache"

New-Item -ItemType Directory -Path $pipCacheDir -Force | Out-Null
$env:PIP_CACHE_DIR = $pipCacheDir

if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw "Python executable not found: $pythonExecutable"
}

if (-not (Test-Path -LiteralPath $requirementsPath)) {
    throw "Requirements file not found: $requirementsPath"
}

if ($UpgradePip) {
    & $pythonExecutable -m pip install --cache-dir $pipCacheDir --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip."
    }
}

& $pythonExecutable -m pip install --cache-dir $pipCacheDir -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install RAG dependencies."
}

if ($IncludeSentenceTransformers) {
    if (-not (Test-Path -LiteralPath $embedRequirementsPath)) {
        throw "Embedding requirements file not found: $embedRequirementsPath"
    }

    & $pythonExecutable -m pip install --cache-dir $pipCacheDir -r $embedRequirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install optional sentence-transformers dependencies."
    }
}

Write-Host ("Installed core RAG dependencies from " + $requirementsPath)
Write-Host ("Pip cache: " + $pipCacheDir)
if ($IncludeSentenceTransformers) {
    Write-Host ("Installed optional embedding dependencies from " + $embedRequirementsPath)
}
