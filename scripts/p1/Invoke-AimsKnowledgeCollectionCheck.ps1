param(
    [string]$SummaryPath,
    [string]$PlanPath,
    [string]$RoutePath,
    [string]$OutputDir,
    [switch]$RefreshCollections
)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "p0\Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$outputRoot = if ($OutputDir) { $OutputDir } else { Join-Path $repoRoot "data\knowledge" }
$summaryFile = if ($SummaryPath) { $SummaryPath } else { Join-Path $outputRoot "knowledge-collection-summary.json" }
$planFile = if ($PlanPath) { $PlanPath } else { Join-Path $outputRoot "knowledge-collection-plan.json" }
$routeFile = if ($RoutePath) { $RoutePath } else { Join-Path $repoRoot "fixtures\knowledge\domain-routing.json" }
$skippedFile = Join-Path $outputRoot "knowledge-collection-skipped.json"

if ($RefreshCollections -or -not (Test-Path -LiteralPath $summaryFile) -or -not (Test-Path -LiteralPath $planFile)) {
    & (Join-Path $PSScriptRoot "Export-AimsKnowledgeCollections.ps1") -OutputDir $outputRoot -RefreshChunks
    if (-not $?) {
        throw "Failed to refresh knowledge collection artifacts."
    }
}

foreach ($requiredPath in @($summaryFile, $planFile, $routeFile, $skippedFile)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required file not found: $requiredPath"
    }
}

$summary = Get-Content -LiteralPath $summaryFile -Raw -Encoding UTF8 | ConvertFrom-Json
$planData = Get-Content -LiteralPath $planFile -Raw -Encoding UTF8 | ConvertFrom-Json
$routeConfig = Get-Content -LiteralPath $routeFile -Raw -Encoding UTF8 | ConvertFrom-Json
$plan = if ($planData -is [System.Array]) { $planData } else { @($planData) }
$rules = if ($routeConfig.collections -is [System.Array]) { $routeConfig.collections } else { @($routeConfig.collections) }
$summaryCollections = if ($summary.byCollection -is [System.Array]) { $summary.byCollection } else { @($summary.byCollection) }

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

Add-Result -Name "collection summary exists" -Passed ($summary.totalRecords -gt 0) -Detail ("records=" + $summary.totalRecords)
Add-Result -Name "collection plan exists" -Passed ($plan.Count -gt 0) -Detail ("entries=" + $plan.Count)
Add-Result -Name "chunk routing coverage" -Passed ($summary.routedChunkRecords -gt 0) -Detail ("routed=" + $summary.routedChunkRecords + "/" + $summary.totalChunkRecords + "; skipped=" + $summary.skippedChunkRecords)
Add-Result -Name "skipped report exists" -Passed (Test-Path -LiteralPath $skippedFile) -Detail $skippedFile

foreach ($rule in @($rules | Where-Object { $_.required })) {
    $collectionName = [string]$rule.collection
    $collectionSummary = @($summaryCollections | Where-Object { $_.collection -eq $collectionName } | Select-Object -First 1)
    $planEntry = @($plan | Where-Object { $_.collection -eq $collectionName } | Select-Object -First 1)

    $hasCollection = ($collectionSummary.Count -gt 0 -and $collectionSummary[0].recordCount -gt 0)
    Add-Result -Name "$collectionName present" -Passed $hasCollection -Detail ($(if ($hasCollection) { "records=" + $collectionSummary[0].recordCount } else { "missing" }))

    if ($collectionSummary.Count -gt 0) {
        Add-Result -Name "$collectionName engine" -Passed ([string]$collectionSummary[0].engine -eq [string]$rule.engine) -Detail ("expected=" + $rule.engine + "; actual=" + $collectionSummary[0].engine)
    }
    else {
        Add-Result -Name "$collectionName engine" -Passed $false -Detail ("expected=" + $rule.engine + "; actual=missing")
    }

    Add-Result -Name "$collectionName in plan" -Passed ($planEntry.Count -gt 0) -Detail ($(if ($planEntry.Count -gt 0) { "plan-ready" } else { "missing" }))
}

$generatedDir = Join-Path $repoRoot ".generated"
if (-not (Test-Path -LiteralPath $generatedDir)) {
    New-Item -ItemType Directory -Path $generatedDir -Force | Out-Null
}

$reportPath = Join-Path $generatedDir "aims.knowledge-collection-check.json"
$reportData = [ordered]@{
    generatedAt        = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    summaryPath        = $summaryFile
    planPath           = $planFile
    totalRecords       = $summary.totalRecords
    routedChunkRecords = $summary.routedChunkRecords
    skippedChunkRecords = $summary.skippedChunkRecords
    results            = @($results.ToArray())
}
$reportData | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8

$results | Format-Table -AutoSize
Write-Host ""
Write-Host ("Knowledge collection check report written to " + $reportPath)

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
