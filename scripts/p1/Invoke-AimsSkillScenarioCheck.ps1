param(
    [string]$CatalogPath,
    [string]$SummaryPath
)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "p0\Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$skillsRoot = Join-Path $repoRoot "skills"
$scenarioPath = if ($CatalogPath) { $CatalogPath } else { Join-Path $repoRoot "fixtures\skills\skill-scenarios.json" }
$summaryFile = if ($SummaryPath) { $SummaryPath } else { Join-Path $repoRoot ".generated\aims.skill-scenario-summary.json" }

if (-not (Test-Path -LiteralPath $scenarioPath)) {
    throw "Scenario catalog not found: $scenarioPath"
}

$catalog = Get-Content -LiteralPath $scenarioPath -Raw -Encoding UTF8 | ConvertFrom-Json
$scenarios = @($catalog.scenarios)
$skillDirs = @(Get-ChildItem -LiteralPath $skillsRoot -Directory | Sort-Object Name)
$skillNames = @($skillDirs | ForEach-Object { $_.Name })
$allowedRiskLevels = @("low", "medium", "high")
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

$duplicateIds = @($scenarios | Group-Object id | Where-Object { $_.Count -gt 1 })
Add-Result -Name "scenario ids unique" -Passed ($duplicateIds.Count -eq 0) -Detail $(if ($duplicateIds.Count -eq 0) { "all unique" } else { ($duplicateIds.Name -join ", ") })

$unknownSkills = @($scenarios | ForEach-Object { $_.skill } | Sort-Object -Unique | Where-Object { $_ -notin $skillNames })
Add-Result -Name "scenario skill mapping" -Passed ($unknownSkills.Count -eq 0) -Detail $(if ($unknownSkills.Count -eq 0) { "all mapped to existing skills" } else { "unknown skills: " + ($unknownSkills -join ", ") })

foreach ($skillDir in $skillDirs) {
    $skill = $skillDir.Name
    $skillFile = Join-Path $skillDir.FullName "SKILL.md"
    $skillContent = Get-Content -LiteralPath $skillFile -Raw -Encoding UTF8
    $skillScenarios = @($scenarios | Where-Object { $_.skill -eq $skill })
    $isMarketSkill = Test-Path -LiteralPath (Join-Path $skillDir.FullName ".clawhub")

    Add-Result -Name "$skill scenario coverage" -Passed ($isMarketSkill -or $skillScenarios.Count -gt 0) -Detail $(if ($isMarketSkill) { "market skill; scenarios optional; scenarios: $($skillScenarios.Count)" } else { "scenarios: $($skillScenarios.Count)" })

    foreach ($scenario in $skillScenarios) {
        $scenarioId = $scenario.id
        $inputKeys = @($scenario.input.PSObject.Properties.Name)
        $requiredOutputKeywords = @($scenario.validation.requiredOutputKeywords)
        $skillMustMention = @($scenario.validation.skillMustMention)
        $riskLevel = [string]$scenario.riskLevel

        Add-Result -Name "$scenarioId metadata" -Passed (
            -not [string]::IsNullOrWhiteSpace($scenario.id) -and
            -not [string]::IsNullOrWhiteSpace($scenario.title) -and
            -not [string]::IsNullOrWhiteSpace($scenario.description) -and
            -not [string]::IsNullOrWhiteSpace($scenario.domain)
        ) -Detail ("skill={0}; domain={1}" -f $scenario.skill, $scenario.domain)

        Add-Result -Name "$scenarioId risk level" -Passed ($riskLevel -in $allowedRiskLevels) -Detail $riskLevel
        Add-Result -Name "$scenarioId input coverage" -Passed ($inputKeys.Count -ge 3) -Detail ($(if ($inputKeys.Count -gt 0) { $inputKeys -join ", " } else { "missing input fields" }))
        Add-Result -Name "$scenarioId validation rules" -Passed ($requiredOutputKeywords.Count -gt 0 -and $skillMustMention.Count -gt 0) -Detail ("outputKeywords={0}; skillMustMention={1}" -f $requiredOutputKeywords.Count, $skillMustMention.Count)

        $missingOutputKeywords = @($requiredOutputKeywords | Where-Object { $skillContent -notmatch [regex]::Escape($_) })
        Add-Result -Name "$scenarioId output keywords" -Passed ($missingOutputKeywords.Count -eq 0) -Detail $(if ($missingOutputKeywords.Count -eq 0) { "covered by SKILL.md output section" } else { "missing: " + ($missingOutputKeywords -join ", ") })

        $missingMustMention = @($skillMustMention | Where-Object { $skillContent -notmatch [regex]::Escape($_) })
        Add-Result -Name "$scenarioId skill anchors" -Passed ($missingMustMention.Count -eq 0) -Detail $(if ($missingMustMention.Count -eq 0) { "all anchor terms present" } else { "missing: " + ($missingMustMention -join ", ") })

        if ([string]$scenario.validation.outputMode -eq "json") {
            Add-Result -Name "$scenarioId json output cue" -Passed ($skillContent -match "```json") -Detail "expects JSON fenced block"
        }
    }
}

$summaryDir = Split-Path -Parent $summaryFile
if (-not (Test-Path -LiteralPath $summaryDir)) {
    New-Item -ItemType Directory -Path $summaryDir -Force | Out-Null
}

$summary = [pscustomobject]@{
    generatedAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    scenarioCatalog = $scenarioPath.Replace($repoRoot + "\", "")
    totalSkills = $skillDirs.Count
    totalScenarios = $scenarios.Count
    byDomain = ($scenarios | Group-Object domain | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{ domain = $_.Name; count = $_.Count }
    })
    byRisk = ($scenarios | Group-Object riskLevel | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{ riskLevel = $_.Name; count = $_.Count }
    })
    bySkill = ($scenarios | Group-Object skill | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{ skill = $_.Name; count = $_.Count }
    })
}

$summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryFile -Encoding UTF8

$results | Format-Table -AutoSize
Write-Host ""
Write-Host "Scenario summary written to $summaryFile"

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
