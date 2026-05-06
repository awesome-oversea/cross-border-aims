param(
    [string]$SkillsRoot,
    [string[]]$Skills
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$skillsRoot = if ($SkillsRoot) { $SkillsRoot } else { Join-Path $repoRoot "skills" }
$requiredSkills = if ($Skills -and $Skills.Count -gt 0) { $Skills } else { @(
    "skill-vetter",
    "skill-manager",
    "find-skills-skill",
    "self-improvement",
    "data-analyst-pro",
    "auto-updater-windows",
    "agent-health-optimizer"
) }

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

foreach ($skill in $requiredSkills) {
    $skillDir = Join-Path $skillsRoot $skill
    $skillFile = Join-Path $skillDir "SKILL.md"
    $exists = Test-Path -LiteralPath $skillFile
    Add-Result -Name "$skill exists" -Passed $exists -Detail $skillFile

    if (-not $exists) {
        continue
    }

    $content = Get-Content -LiteralPath $skillFile -Raw -Encoding UTF8
    $frontmatterMatch = [regex]::Match($content, "(?s)^---\s*\r?\n(.*?)\r?\n---")
    Add-Result -Name "$skill frontmatter" -Passed $frontmatterMatch.Success -Detail "Requires YAML frontmatter with name and description"

    if (-not $frontmatterMatch.Success) {
        continue
    }

    $frontmatter = $frontmatterMatch.Groups[1].Value
    $nameMatch = [regex]::Match($frontmatter, "(?m)^name:\s*(.+?)\s*$")
    $descriptionMatch = [regex]::Match($frontmatter, "(?m)^description:\s*(.+?)\s*$")

    Add-Result -Name "$skill name field" -Passed ($nameMatch.Success -and -not [string]::IsNullOrWhiteSpace($nameMatch.Groups[1].Value)) -Detail $(if ($nameMatch.Success) { $nameMatch.Groups[1].Value.Trim() } else { "missing" })
    Add-Result -Name "$skill description field" -Passed ($descriptionMatch.Success -and -not [string]::IsNullOrWhiteSpace($descriptionMatch.Groups[1].Value)) -Detail $(if ($descriptionMatch.Success) { $descriptionMatch.Groups[1].Value.Trim() } else { "missing" })
}

$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
