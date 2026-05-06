param(
    [string]$OutputPath,
    [string]$ScenarioCatalogPath
)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "p0\Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$skillsRoot = Join-Path $repoRoot "skills"
$scenarioPath = if ($ScenarioCatalogPath) { $ScenarioCatalogPath } else { Join-Path $repoRoot "fixtures\skills\skill-scenarios.json" }
$catalogPath = if ($OutputPath) { $OutputPath } else { Join-Path $repoRoot ".generated\aims.skill-catalog.json" }

if (-not (Test-Path -LiteralPath $skillsRoot)) {
    throw "Skills directory not found: $skillsRoot"
}

$scenarioMap = @{}
if (Test-Path -LiteralPath $scenarioPath) {
    $scenarioCatalog = Get-Content -LiteralPath $scenarioPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($scenario in @($scenarioCatalog.scenarios)) {
        if (-not $scenarioMap.ContainsKey($scenario.skill)) {
            $scenarioMap[$scenario.skill] = New-Object System.Collections.Generic.List[object]
        }

        $scenarioMap[$scenario.skill].Add($scenario)
    }
}

$catalog = New-Object System.Collections.Generic.List[object]

foreach ($skillDir in (Get-ChildItem -LiteralPath $skillsRoot -Directory | Sort-Object Name)) {
    $skillFile = Join-Path $skillDir.FullName "SKILL.md"
    if (-not (Test-Path -LiteralPath $skillFile)) {
        continue
    }

    $content = Get-Content -LiteralPath $skillFile -Raw -Encoding UTF8
    $frontmatterMatch = [regex]::Match($content, "(?s)^---\s*\r?\n(.*?)\r?\n---")
    $frontmatter = if ($frontmatterMatch.Success) { $frontmatterMatch.Groups[1].Value } else { "" }
    $nameMatch = [regex]::Match($frontmatter, "(?m)^name:\s*(.+?)\s*$")
    $descriptionMatch = [regex]::Match($frontmatter, "(?m)^description:\s*(.+?)\s*$")
    $sections = @([regex]::Matches($content, "(?m)^##\s+(.+?)\s*$") | ForEach-Object { $_.Groups[1].Value.Trim() })
    $scenarioArrayObject = if ($scenarioMap.ContainsKey($skillDir.Name)) { $scenarioMap[$skillDir.Name].ToArray() } else { @() }
    $scenarioItems = if ($scenarioArrayObject -is [System.Array]) { $scenarioArrayObject } else { @($scenarioArrayObject) }
    $knowledgeScenarioCount = @($scenarioItems | Where-Object { $_.requiresKnowledge }).Length
    $manualGateScenarioCount = @($scenarioItems | Where-Object {
        $_.validation -and
        $_.validation.PSObject.Properties.Name -contains "manualGateRequired" -and
        $_.validation.manualGateRequired
    }).Length
    $scenarioCount = ($scenarioItems | Measure-Object).Count
    $scenarioIds = @($scenarioItems | ForEach-Object { $_.id })
    $domains = @($scenarioItems | ForEach-Object { $_.domain } | Sort-Object -Unique)
    $riskLevels = @($scenarioItems | ForEach-Object { $_.riskLevel } | Sort-Object -Unique)

    $catalog.Add([pscustomobject]@{
        id                         = $skillDir.Name
        name                       = $(if ($nameMatch.Success) { $nameMatch.Groups[1].Value.Trim() } else { $skillDir.Name })
        description                = $(if ($descriptionMatch.Success) { $descriptionMatch.Groups[1].Value.Trim() } else { "" })
        sourcePath                 = $skillFile.Replace($repoRoot + "\", "")
        sections                   = $sections
        outputMode                 = $(if ($content -match "```json") { "json" } else { "list" })
        requiresKnowledgeRetrieval = ($knowledgeScenarioCount -gt 0)
        requiresManualGate         = ($manualGateScenarioCount -gt 0)
        scenarioCount              = $scenarioCount
        scenarioIds                = $scenarioIds
        domains                    = $domains
        riskLevels                 = $riskLevels
    })
}

$catalogDir = Split-Path -Parent $catalogPath
if (-not (Test-Path -LiteralPath $catalogDir)) {
    New-Item -ItemType Directory -Path $catalogDir -Force | Out-Null
}

$catalog | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $catalogPath -Encoding UTF8

Write-Host "Skill catalog written to $catalogPath"
Write-Host ("Skills exported: " + $catalog.Count)
Write-Host ("Skills with scenario fixtures: " + (($catalog | Where-Object { $_.scenarioCount -gt 0 } | Measure-Object).Count))
