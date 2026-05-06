param(
    [string]$OutputDir
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$outputRoot = if ($OutputDir) { $OutputDir } else { Join-Path $repoRoot "data\knowledge" }

$knowledgeRoot = Get-ChildItem -LiteralPath $repoRoot -Directory | Where-Object {
    (Test-Path -LiteralPath (Join-Path $_.FullName "README.md")) -and
    @((Get-ChildItem -LiteralPath $_.FullName -Directory | Where-Object { $_.Name -match '^\d{2}-' })).Count -ge 5
} | Select-Object -First 1 -ExpandProperty FullName

if (-not $knowledgeRoot) {
    throw "Unable to locate the local knowledge-base root directory."
}

if (-not (Test-Path -LiteralPath $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
}

$categoryConfig = @{
    "00" = @{ key = "general";      batch = "P0-foundation";    priority = "normal"; tags = @("ai-agent", "foundation") }
    "01" = @{ key = "deploy";       batch = "P0-foundation";    priority = "high";   tags = @("deployment", "gateway") }
    "02" = @{ key = "architecture"; batch = "P0-foundation";    priority = "high";   tags = @("architecture", "core") }
    "03" = @{ key = "config";       batch = "P0-foundation";    priority = "high";   tags = @("config", "operations") }
    "04" = @{ key = "channels";     batch = "P1-integrations";  priority = "high";   tags = @("channels", "integration") }
    "05" = @{ key = "agents";       batch = "P0-foundation";    priority = "high";   tags = @("agent", "memory") }
    "06" = @{ key = "skills";       batch = "P1-capabilities";  priority = "high";   tags = @("skills", "workflow") }
    "07" = @{ key = "mcp";          batch = "P1-capabilities";  priority = "high";   tags = @("mcp", "tools") }
    "08" = @{ key = "ops";          batch = "P0-foundation";    priority = "normal"; tags = @("automation", "ops") }
    "09" = @{ key = "security";     batch = "P0-foundation";    priority = "high";   tags = @("security", "permissions") }
    "10" = @{ key = "enterprise";   batch = "P2-expansion";     priority = "normal"; tags = @("enterprise", "best-practice") }
    "11" = @{ key = "governance";   batch = "P2-expansion";     priority = "normal"; tags = @("governance", "sources") }
}

$extraDocPatterns = @(
    @{ pattern = "AIMS*OpenClaw*.md"; batch = "P0-foundation"; priority = "high"; tags = @("project", "deployment") },
    @{ pattern = "AI*OpenClaw*V2.md"; batch = "P0-foundation"; priority = "high"; tags = @("project", "solution") },
    @{ pattern = "AIMS*开发方案*.md"; batch = "P0-foundation"; priority = "high"; tags = @("project", "delivery") },
    @{ pattern = "AIMS*项目计划*.md"; batch = "P0-foundation"; priority = "high"; tags = @("project", "plan") }
)

function New-ManifestEntry {
    param(
        [string]$Path,
        [string]$CategoryKey,
        [string]$CategoryName,
        [string]$ImportBatch,
        [string]$Priority,
        [string[]]$Tags,
        [string]$SourceGroup
    )

    $content = Get-Content -LiteralPath $Path -Raw
    $charCount = $content.Length
    $suggestedChunkChars = 800
    $suggestedChunkCount = [Math]::Max(1, [Math]::Ceiling($charCount / $suggestedChunkChars))
    $relativePath = $Path.Replace($repoRoot + "\", "")
    $title = [System.IO.Path]::GetFileNameWithoutExtension($Path)

    return [pscustomobject]@{
        id                  = ($relativePath -replace "[\\/:\s]+", "-").ToLowerInvariant()
        title               = $title
        sourcePath          = $relativePath
        sourceGroup         = $SourceGroup
        categoryKey         = $CategoryKey
        categoryName        = $CategoryName
        importBatch         = $ImportBatch
        priority            = $Priority
        tags                = $Tags
        charCount           = $charCount
        suggestedChunkChars = $suggestedChunkChars
        suggestedChunkCount = $suggestedChunkCount
    }
}

$entries = New-Object System.Collections.Generic.List[object]

$knowledgeFiles = Get-ChildItem -LiteralPath $knowledgeRoot -Recurse -File -Filter "*.md" | Sort-Object FullName
foreach ($file in $knowledgeFiles) {
    $relative = $file.FullName.Substring($knowledgeRoot.Length).TrimStart('\')
    $segments = $relative -split "[\\/]"
    $topDir = if ($segments.Length -gt 1) { $segments[0] } else { "root" }

    if ($topDir -eq "root") {
        $categoryKey = "general"
        $categoryName = "knowledge-root"
        $batch = "P0-foundation"
        $priority = "normal"
        $tags = @("knowledge-base")
    }
    else {
        $prefixMatch = [regex]::Match($topDir, '^(\d{2})-')
        $prefix = if ($prefixMatch.Success) { $prefixMatch.Groups[1].Value } else { "00" }
        $config = $categoryConfig[$prefix]
        $categoryKey = $config.key
        $categoryName = $topDir
        $batch = $config.batch
        $priority = $config.priority
        $tags = @($config.tags)
    }

    $entries.Add((New-ManifestEntry -Path $file.FullName -CategoryKey $categoryKey -CategoryName $categoryName -ImportBatch $batch -Priority $priority -Tags $tags -SourceGroup "knowledge-base"))
}

$extraDocPaths = New-Object System.Collections.Generic.HashSet[string]
foreach ($patternConfig in $extraDocPatterns) {
    foreach ($file in (Get-ChildItem -LiteralPath $repoRoot -File -Filter "*.md" | Where-Object { $_.Name -like $patternConfig.pattern })) {
        if ($extraDocPaths.Add($file.FullName)) {
            $entries.Add((New-ManifestEntry -Path $file.FullName -CategoryKey "project" -CategoryName "project-doc" -ImportBatch $patternConfig.batch -Priority $patternConfig.priority -Tags $patternConfig.tags -SourceGroup "project-doc"))
        }
    }
}

$manifestPath = Join-Path $outputRoot "knowledge-manifest.json"
$summaryPath = Join-Path $outputRoot "knowledge-summary.json"

$entries | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

$summary = [pscustomobject]@{
    generatedAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    knowledgeRoot = $knowledgeRoot.Replace($repoRoot + "\", "")
    totalDocs   = $entries.Count
    byBatch     = ($entries | Group-Object importBatch | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{ batch = $_.Name; count = $_.Count }
    })
    byCategory  = ($entries | Group-Object categoryName | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{ category = $_.Name; count = $_.Count }
    })
}

$summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host "Knowledge manifest written to $manifestPath"
Write-Host "Knowledge summary written to $summaryPath"
Write-Host ("Documents indexed: " + $entries.Count)
