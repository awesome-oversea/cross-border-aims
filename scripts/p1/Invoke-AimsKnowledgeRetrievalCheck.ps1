param(
    [string]$PythonPath = ".\.venv\Scripts\python.exe",
    [string]$QueryCasePath,
    [string]$RecordsPath,
    [string]$OutputPath,
    [ValidateSet("hash-bow", "sentence-transformers")]
    [string]$EmbeddingBackend = "hash-bow",
    [string]$ModelName = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    [int]$VectorDimension = 384,
    [string]$MilvusUri,
    [string]$QdrantUrl,
    [int]$TopK = 5,
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "p0\Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
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
$caseFile = if ($QueryCasePath) { $QueryCasePath } else { Join-Path $repoRoot "fixtures\knowledge\query-cases.json" }
$recordFile = if ($RecordsPath) { $RecordsPath } else { Join-Path $repoRoot "data\knowledge\knowledge-collection-records.jsonl" }
$reportFile = if ($OutputPath) { $OutputPath } else { Join-Path $repoRoot ".generated\aims.knowledge-retrieval-check.json" }
$pythonScript = Join-Path $PSScriptRoot "aims_knowledge_rag.py"

foreach ($requiredPath in @($pythonExecutable, $pythonScript, $caseFile)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required file not found: $requiredPath"
    }
}

if ($Offline -and -not (Test-Path -LiteralPath $recordFile)) {
    throw "Offline records file not found: $recordFile"
}

$arguments = @(
    $pythonScript,
    "check",
    "--query-case-path", $caseFile,
    "--report-path", $reportFile,
    "--embedding-backend", $EmbeddingBackend,
    "--model-name", $ModelName,
    "--vector-dimension", $VectorDimension,
    "--milvus-uri", $resolvedMilvusUri,
    "--qdrant-url", $resolvedQdrantUrl,
    "--top-k", $TopK
)

if ($Offline) {
    $arguments += @("--offline", "--records-path", $recordFile)
}

& $pythonExecutable @arguments
exit $LASTEXITCODE
