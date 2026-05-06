param(
    [string]$PythonPath = ".\.venv\Scripts\python.exe",
    [string]$RecordsPath,
    [string]$PlanPath,
    [string]$OutputPath,
    [ValidateSet("hash-bow", "sentence-transformers")]
    [string]$EmbeddingBackend = "hash-bow",
    [string]$ModelName = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    [int]$VectorDimension = 384,
    [string]$MilvusUri,
    [string]$QdrantUrl,
    [int]$BatchSize = 32,
    [switch]$RefreshCollections,
    [switch]$RecreateExisting,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "p0\Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$outputRoot = Join-Path $repoRoot "data\knowledge"
$envFile = Join-Path $repoRoot ".env"
$envMap = Read-AimsDotEnv -Path $envFile
$resolvedMilvusUri = if ([string]::IsNullOrWhiteSpace($MilvusUri)) {
    $milvusPort = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_MILVUS_GRPC_PORT" -Default "19530"
    "http://127.0.0.1:$milvusPort"
}
else {
    $MilvusUri
}
$resolvedQdrantUrl = if ([string]::IsNullOrWhiteSpace($QdrantUrl)) {
    $qdrantPort = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_QDRANT_HTTP_PORT" -Default "6333"
    "http://127.0.0.1:$qdrantPort"
}
else {
    $QdrantUrl
}
$pythonExecutable = if ([System.IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $repoRoot $PythonPath }
$recordFile = if ($RecordsPath) { $RecordsPath } else { Join-Path $outputRoot "knowledge-collection-records.jsonl" }
$planFile = if ($PlanPath) { $PlanPath } else { Join-Path $outputRoot "knowledge-collection-plan.json" }
$reportFile = if ($OutputPath) { $OutputPath } else { Join-Path $repoRoot ".generated\aims.knowledge-import-report.json" }
$pythonScript = Join-Path $PSScriptRoot "aims_knowledge_rag.py"

if ($RefreshCollections) {
    & (Join-Path $PSScriptRoot "Export-AimsKnowledgeCollections.ps1") -RefreshChunks -OutputDir $outputRoot
    if (-not $?) {
        throw "Failed to refresh knowledge collection artifacts."
    }
}

foreach ($requiredPath in @($pythonExecutable, $pythonScript, $recordFile, $planFile)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required file not found: $requiredPath"
    }
}

$arguments = @(
    $pythonScript,
    "import",
    "--records-path", $recordFile,
    "--plan-path", $planFile,
    "--report-path", $reportFile,
    "--embedding-backend", $EmbeddingBackend,
    "--model-name", $ModelName,
    "--vector-dimension", $VectorDimension,
    "--milvus-uri", $resolvedMilvusUri,
    "--qdrant-url", $resolvedQdrantUrl,
    "--batch-size", $BatchSize
)

if ($RecreateExisting) {
    $arguments += "--recreate-existing"
}

if ($DryRun) {
    $arguments += "--dry-run"
}

& $pythonExecutable @arguments
exit $LASTEXITCODE
