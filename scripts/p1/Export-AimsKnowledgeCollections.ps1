param(
    [string]$ChunkPath,
    [string]$RoutePath,
    [string]$SeedPath,
    [string]$SkillScenarioPath,
    [string]$OutputDir,
    [switch]$RefreshChunks
)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "p0\Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$outputRoot = if ($OutputDir) { $OutputDir } else { Join-Path $repoRoot "data\knowledge" }
$chunkFile = if ($ChunkPath) { $ChunkPath } else { Join-Path $outputRoot "knowledge-chunks.jsonl" }
$routeFile = if ($RoutePath) { $RoutePath } else { Join-Path $repoRoot "fixtures\knowledge\domain-routing.json" }
$seedFile = if ($SeedPath) { $SeedPath } else { Join-Path $repoRoot "fixtures\knowledge\domain-seeds.json" }
$skillScenarioFile = if ($SkillScenarioPath) { $SkillScenarioPath } else { Join-Path $repoRoot "fixtures\skills\skill-scenarios.json" }

if ($RefreshChunks -or -not (Test-Path -LiteralPath $chunkFile)) {
    & (Join-Path $PSScriptRoot "Export-AimsKnowledgeChunks.ps1") -OutputDir $outputRoot -RefreshManifest
    if (-not $?) {
        throw "Failed to refresh knowledge chunks."
    }
}

foreach ($requiredPath in @($chunkFile, $routeFile, $seedFile, $skillScenarioFile)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required file not found: $requiredPath"
    }
}

if (-not (Test-Path -LiteralPath $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
}

function Get-RelativePath {
    param(
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $Path
    }

    if ($Path.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $Path.Substring($repoRoot.Length).TrimStart("\")
    }

    return $Path
}

function ConvertTo-ObjectArray {
    param(
        [object]$Value
    )

    if ($null -eq $Value) {
        return @()
    }

    if ($Value -is [System.Array]) {
        return $Value
    }

    return @($Value)
}

function Get-ObjectPropertyValue {
    param(
        [object]$InputObject,
        [string]$Name,
        [object]$Default = $null
    )

    if ($null -eq $InputObject) {
        return $Default
    }

    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $Default
    }

    return $property.Value
}

function Import-Jsonl {
    param(
        [string]$Path
    )

    $items = New-Object System.Collections.Generic.List[object]
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $items.Add(($line | ConvertFrom-Json))
    }

    return $items.ToArray()
}

function Get-TextMatch {
    param(
        [string]$Text,
        [object]$Terms,
        [int]$Weight = 1
    )

    $termsArray = @(ConvertTo-ObjectArray -Value $Terms)
    $matched = New-Object System.Collections.Generic.HashSet[string]

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return [pscustomobject]@{
            Score   = 0
            Matches = @()
        }
    }

    $haystack = $Text.ToLowerInvariant()
    foreach ($term in $termsArray) {
        $value = [string]$term
        if ([string]::IsNullOrWhiteSpace($value)) {
            continue
        }

        if ($haystack.Contains($value.ToLowerInvariant())) {
            $matched.Add($value) | Out-Null
        }
    }

    return [pscustomobject]@{
        Score   = $matched.Count * $Weight
        Matches = @($matched)
    }
}

function Resolve-ChunkRoute {
    param(
        [object]$Chunk,
        [object[]]$Rules,
        [int]$DefaultMinimumScore
    )

    $searchText = (@(
        [string]$Chunk.title,
        [string]$Chunk.sourcePath,
        [string]$Chunk.categoryKey,
        [string]$Chunk.categoryName,
        [string]$Chunk.importBatch,
        [string]$Chunk.text
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n"

    $titleText = (@([string]$Chunk.title, [string]$Chunk.categoryName) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n"
    $pathText = (@([string]$Chunk.sourcePath, [string]$Chunk.sourceGroup) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n"

    $best = $null
    foreach ($rule in $Rules) {
        $score = 0
        $reasons = New-Object System.Collections.Generic.List[string]

        $importBatches = @(ConvertTo-ObjectArray -Value (Get-ObjectPropertyValue -InputObject $rule -Name "importBatches"))
        if ($importBatches.Count -gt 0 -and [string]$Chunk.importBatch -in $importBatches) {
            $score += 2
            $reasons.Add("importBatch:$($Chunk.importBatch)") | Out-Null
        }

        $categoryKeys = @(ConvertTo-ObjectArray -Value (Get-ObjectPropertyValue -InputObject $rule -Name "categoryKeys"))
        if ($categoryKeys.Count -gt 0 -and [string]$Chunk.categoryKey -in $categoryKeys) {
            $score += 2
            $reasons.Add("category:$($Chunk.categoryKey)") | Out-Null
        }

        $sourceGroups = @(ConvertTo-ObjectArray -Value (Get-ObjectPropertyValue -InputObject $rule -Name "sourceGroups"))
        if ($sourceGroups.Count -gt 0 -and [string]$Chunk.sourceGroup -in $sourceGroups) {
            $score += 1
            $reasons.Add("sourceGroup:$($Chunk.sourceGroup)") | Out-Null
        }

        $titleMatches = Get-TextMatch -Text $titleText -Terms (Get-ObjectPropertyValue -InputObject $rule -Name "titleKeywords") -Weight 3
        $score += $titleMatches.Score
        foreach ($match in $titleMatches.Matches) {
            $reasons.Add("title:$match") | Out-Null
        }

        $pathMatches = Get-TextMatch -Text $pathText -Terms (Get-ObjectPropertyValue -InputObject $rule -Name "sourcePathKeywords") -Weight 2
        $score += $pathMatches.Score
        foreach ($match in $pathMatches.Matches) {
            $reasons.Add("path:$match") | Out-Null
        }

        $textMatches = Get-TextMatch -Text $searchText -Terms (Get-ObjectPropertyValue -InputObject $rule -Name "textKeywords") -Weight 1
        $score += $textMatches.Score
        foreach ($match in $textMatches.Matches) {
            $reasons.Add("text:$match") | Out-Null
        }

        $ruleMinimumScore = Get-ObjectPropertyValue -InputObject $rule -Name "minimumScore"
        $minimumScore = if ($null -ne $ruleMinimumScore) { [int]$ruleMinimumScore } else { $DefaultMinimumScore }
        if ($score -lt $minimumScore) {
            continue
        }

        if ($null -eq $best -or $score -gt $best.Score) {
            $best = [pscustomobject]@{
                Collection = [string]$rule.collection
                Engine     = [string]$rule.engine
                Domain     = [string]$rule.domain
                Score      = $score
                Reasons    = @($reasons)
            }
        }
    }

    return $best
}

$routeConfig = Get-Content -LiteralPath $routeFile -Raw -Encoding UTF8 | ConvertFrom-Json
$routeRules = @(ConvertTo-ObjectArray -Value $routeConfig.collections)
$defaultMinimumScore = if ($null -ne $routeConfig.minimumScore) { [int]$routeConfig.minimumScore } else { 4 }
$collectionMap = @{}
foreach ($rule in $routeRules) {
    $collectionMap[[string]$rule.collection] = $rule
}

$skillRouteMap = @{}
foreach ($skillRoute in @(ConvertTo-ObjectArray -Value $routeConfig.skillRoutes)) {
    $skillRouteMap[[string]$skillRoute.skill] = $skillRoute
}

$chunkRecords = Import-Jsonl -Path $chunkFile
$seedConfig = Get-Content -LiteralPath $seedFile -Raw -Encoding UTF8 | ConvertFrom-Json
$seedRecords = @(ConvertTo-ObjectArray -Value $seedConfig.records)
$skillScenarioConfig = Get-Content -LiteralPath $skillScenarioFile -Raw -Encoding UTF8 | ConvertFrom-Json
$skillScenarios = @(ConvertTo-ObjectArray -Value $skillScenarioConfig.scenarios)

$records = New-Object System.Collections.Generic.List[object]
$skippedChunks = New-Object System.Collections.Generic.List[object]

foreach ($chunk in $chunkRecords) {
    $route = Resolve-ChunkRoute -Chunk $chunk -Rules $routeRules -DefaultMinimumScore $defaultMinimumScore
    if ($null -eq $route) {
        $skippedChunks.Add([pscustomobject]@{
            id         = [string]$chunk.id
            title      = [string]$chunk.title
            sourcePath = [string]$chunk.sourcePath
            importBatch = [string]$chunk.importBatch
        })
        continue
    }

    $records.Add([pscustomobject]@{
        recordId       = "chunk-$($chunk.id)"
        sourceType     = "chunk"
        sourceId       = [string]$chunk.id
        collection     = $route.Collection
        engine         = $route.Engine
        domain         = $route.Domain
        title          = [string]$chunk.title
        text           = [string]$chunk.text
        tags           = @($chunk.tags)
        sourcePath     = [string]$chunk.sourcePath
        routingScore   = $route.Score
        routingReasons = @($route.Reasons)
        metadata       = [pscustomobject]@{
            sourceGroup    = [string]$chunk.sourceGroup
            importBatch    = [string]$chunk.importBatch
            categoryKey    = [string]$chunk.categoryKey
            categoryName   = [string]$chunk.categoryName
            priority       = [string]$chunk.priority
            chunkIndex     = $chunk.chunkIndex
            chunkCount     = $chunk.chunkCount
            collectionHint = [string]$chunk.collectionHint
            engineHint     = [string]$chunk.engineHint
        }
    })
}

foreach ($seed in $seedRecords) {
    $collectionName = [string]$seed.collection
    if (-not $collectionMap.ContainsKey($collectionName)) {
        throw "Seed record references unknown collection: $collectionName"
    }

    $rule = $collectionMap[$collectionName]
    $records.Add([pscustomobject]@{
        recordId       = "seed-$($seed.id)"
        sourceType     = "seed-fixture"
        sourceId       = [string]$seed.id
        collection     = $collectionName
        engine         = [string]$rule.engine
        domain         = [string]$rule.domain
        title          = [string]$seed.title
        text           = [string]$seed.text
        tags           = @($seed.tags)
        sourcePath     = (Get-RelativePath -Path $seedFile)
        routingScore   = 100
        routingReasons = @("seed:$collectionName")
        metadata       = [pscustomobject]@{
            priority = [string]$seed.priority
            version  = $seedConfig.version
        }
    })
}

foreach ($scenario in $skillScenarios) {
    $skillName = [string]$scenario.skill
    if (-not $skillRouteMap.ContainsKey($skillName)) {
        continue
    }

    $skillRoute = $skillRouteMap[$skillName]
    $collectionName = [string]$skillRoute.collection
    if (-not $collectionMap.ContainsKey($collectionName)) {
        throw "Skill route references unknown collection: $collectionName"
    }

    $rule = $collectionMap[$collectionName]
    $scenarioTextParts = @(
        ("Scenario: " + [string]$scenario.title),
        ("Description: " + [string]$scenario.description),
        ("Input: " + (($scenario.input | ConvertTo-Json -Depth 10 -Compress))),
        ("Validation: " + (($scenario.validation | ConvertTo-Json -Depth 10 -Compress)))
    )

    $records.Add([pscustomobject]@{
        recordId       = "scenario-$($scenario.id)"
        sourceType     = "skill-scenario"
        sourceId       = [string]$scenario.id
        collection     = $collectionName
        engine         = [string]$rule.engine
        domain         = [string]$rule.domain
        title          = [string]$scenario.title
        text           = (($scenarioTextParts | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n")
        tags           = @([string]$scenario.skill, [string]$scenario.domain, [string]$scenario.riskLevel)
        sourcePath     = (Get-RelativePath -Path $skillScenarioFile)
        routingScore   = 100
        routingReasons = @("skill:$skillName")
        metadata       = [pscustomobject]@{
            requiresKnowledge = [bool]$scenario.requiresKnowledge
            riskLevel         = [string]$scenario.riskLevel
            outputMode        = [string]$scenario.validation.outputMode
        }
    })
}

$recordPath = Join-Path $outputRoot "knowledge-collection-records.jsonl"
$summaryPath = Join-Path $outputRoot "knowledge-collection-summary.json"
$planPath = Join-Path $outputRoot "knowledge-collection-plan.json"
$skippedPath = Join-Path $outputRoot "knowledge-collection-skipped.json"

$recordLines = foreach ($record in $records) {
    $record | ConvertTo-Json -Compress -Depth 10
}
$recordLines | Set-Content -LiteralPath $recordPath -Encoding UTF8

$skippedChunks | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $skippedPath -Encoding UTF8

$summary = [pscustomobject]@{
    generatedAt        = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    routePath          = (Get-RelativePath -Path $routeFile)
    seedPath           = (Get-RelativePath -Path $seedFile)
    skillScenarioPath  = (Get-RelativePath -Path $skillScenarioFile)
    chunkPath          = (Get-RelativePath -Path $chunkFile)
    totalChunkRecords  = $chunkRecords.Count
    routedChunkRecords = @($records | Where-Object { $_.sourceType -eq "chunk" }).Count
    skippedChunkRecords = $skippedChunks.Count
    totalRecords       = $records.Count
    sourceTypeCounts   = (@($records | Group-Object sourceType | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{
            sourceType = $_.Name
            count      = $_.Count
        }
    }))
    byCollection       = (@($records | Group-Object collection | Sort-Object Name | ForEach-Object {
        $name = $_.Name
        $rule = $collectionMap[$name]
        [pscustomobject]@{
            collection  = $name
            engine      = [string]$rule.engine
            domain      = [string]$rule.domain
            recordCount = $_.Count
            sourceCount = (@($_.Group | Select-Object -ExpandProperty sourceId -Unique)).Count
            sourceTypes = @($_.Group | Group-Object sourceType | Sort-Object Name | ForEach-Object {
                [pscustomobject]@{
                    sourceType = $_.Name
                    count      = $_.Count
                }
            })
            sampleTitles = @($_.Group | Select-Object -First 3 -ExpandProperty title)
        }
    }))
}
$summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

$plan = @($summary.byCollection | Sort-Object collection | ForEach-Object {
    $rule = $collectionMap[$_.collection]
    [pscustomobject]@{
        collection     = $_.collection
        engine         = $_.engine
        domain         = $_.domain
        recordCount    = $_.recordCount
        sourceCount    = $_.sourceCount
        importOrder    = $rule.importOrder
        required       = [bool]$rule.required
        suggestedTopK  = 5
        vectorStrategy = "embedding-pending"
    }
})
$plan | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $planPath -Encoding UTF8

Write-Host "Knowledge collection records written to $recordPath"
Write-Host "Knowledge collection summary written to $summaryPath"
Write-Host "Knowledge collection plan written to $planPath"
Write-Host "Knowledge collection skipped report written to $skippedPath"
Write-Host ("Chunk routing: " + $summary.routedChunkRecords + "/" + $summary.totalChunkRecords)
Write-Host ("Collection records: " + $summary.totalRecords)

if ($records.Count -eq 0) {
    exit 1
}

exit 0
