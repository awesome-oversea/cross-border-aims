param(
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"

$repoRoot = if ($RepoRoot) { $RepoRoot } else { Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) }
$skillsRoot = Join-Path $repoRoot "skills"
$scenarioPath = Join-Path $repoRoot "fixtures\skills\skill-scenarios.json"

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

$inventory = foreach ($skillDir in Get-ChildItem -LiteralPath $skillsRoot -Directory | Sort-Object Name) {
    $skillFile = Join-Path $skillDir.FullName "SKILL.md"
    $frontmatterName = ""
    $frontmatterDescription = ""

    if (Test-Path -LiteralPath $skillFile) {
        $content = Get-Content -LiteralPath $skillFile -Raw -Encoding UTF8
        $frontmatterMatch = [regex]::Match($content, "(?s)^---\s*\r?\n(.*?)\r?\n---")
        if ($frontmatterMatch.Success) {
            $frontmatter = $frontmatterMatch.Groups[1].Value
            $nameMatch = [regex]::Match($frontmatter, "(?m)^name:\s*(.+?)\s*$")
            $descriptionMatch = [regex]::Match($frontmatter, "(?m)^description:\s*(.+?)\s*$")
            if ($nameMatch.Success) {
                $frontmatterName = $nameMatch.Groups[1].Value.Trim()
            }
            if ($descriptionMatch.Success) {
                $frontmatterDescription = $descriptionMatch.Groups[1].Value.Trim()
            }
        }
    }

    $scenarioItems = @()
    if ($scenarioMap.ContainsKey($skillDir.Name)) {
        $scenarioItems = @($scenarioMap[$skillDir.Name].ToArray())
    }
    $domains = @($scenarioItems | ForEach-Object { $_.domain } | Sort-Object -Unique)
    $riskLevels = @($scenarioItems | ForEach-Object { $_.riskLevel } | Sort-Object -Unique)

    [pscustomobject]@{
        id = $skillDir.Name
        name = if ([string]::IsNullOrWhiteSpace($frontmatterName)) { $skillDir.Name } else { $frontmatterName }
        description = $frontmatterDescription
        source = if (Test-Path -LiteralPath (Join-Path $skillDir.FullName ".clawhub")) { "market" } else { "custom" }
        hasSkillFile = (Test-Path -LiteralPath $skillFile)
        hasScenario = ($scenarioItems.Count -gt 0)
        scenarioCount = $scenarioItems.Count
        domains = $domains
        riskLevels = $riskLevels
        hasScripts = (Test-Path -LiteralPath (Join-Path $skillDir.FullName "scripts"))
    }
}

$result = [pscustomobject]@{
    generatedAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    repoRoot = $repoRoot
    totalSkills = @($inventory).Count
    marketSkills = @($inventory | Where-Object { $_.source -eq "market" }).Count
    customSkills = @($inventory | Where-Object { $_.source -eq "custom" }).Count
    missingScenarioCoverage = @($inventory | Where-Object { -not $_.hasScenario } | ForEach-Object { $_.id })
    skills = @($inventory)
}

$result | ConvertTo-Json -Depth 8
