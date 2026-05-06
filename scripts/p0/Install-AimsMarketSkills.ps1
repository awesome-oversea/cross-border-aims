param(
    [string]$SkillsRoot,
    [string]$EnvPath,
    [string[]]$Skills,
    [switch]$Force,
    [switch]$ForceSuspicious,
    [switch]$SkipCheck
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$skillsRoot = if ($SkillsRoot) { $SkillsRoot } else { Join-Path $repoRoot "skills" }
$envPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
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

function Invoke-ClawHub {
    param(
        [string[]]$CommandArgs
    )

    if (Test-Path -LiteralPath $envPath) {
        & (Join-Path $PSScriptRoot "Initialize-AimsLocalStorage.ps1") -EnvPath $envPath -AsJson | Out-Null
        $envMap = Read-AimsDotEnv -Path $envPath
        $npmCacheDir = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_NPM_CACHE_DIR" -Default "D:/aitools/npm-cache"
        $clawHubCacheDir = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_CLAWHUB_CACHE_DIR" -Default "D:/aitools/clawhub-cache"
        New-Item -ItemType Directory -Path $npmCacheDir -Force | Out-Null
        New-Item -ItemType Directory -Path $clawHubCacheDir -Force | Out-Null
        $env:npm_config_cache = $npmCacheDir
        $env:NPM_CONFIG_CACHE = $npmCacheDir
        $env:CLAWHUB_CACHE_DIR = $clawHubCacheDir
    }

    $npxCommand = Get-Command npx.cmd -ErrorAction SilentlyContinue
    if ($null -eq $npxCommand) {
        $npxPsCommand = Get-Command npx -ErrorAction SilentlyContinue
        if ($null -eq $npxPsCommand) {
            throw "npx is not available on PATH."
        }

        $candidateCmd = Join-Path (Split-Path -Parent $npxPsCommand.Source) "npx.cmd"
        if (-not (Test-Path -LiteralPath $candidateCmd)) {
            throw "npx.cmd not found next to $($npxPsCommand.Source)"
        }

        $npxPath = $candidateCmd
    }
    else {
        $npxPath = $npxCommand.Source
    }

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process -FilePath $npxPath -ArgumentList (@("-y", "clawhub@latest") + $CommandArgs) -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { "" }
        $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { "" }
        $output = @($stdout, $stderr) -join [System.Environment]::NewLine
        $exitCode = $process.ExitCode
    }
    finally {
        Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output   = $output.Trim()
    }
}

function Invoke-ClawHubWithRetry {
    param(
        [string[]]$CommandArgs,
        [int]$MaxAttempts = 4
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $response = Invoke-ClawHub -CommandArgs $CommandArgs
        if ($response.ExitCode -eq 0) {
            return $response
        }

        if ($response.Output -match "Rate limit exceeded" -and $attempt -lt $MaxAttempts) {
            Start-Sleep -Seconds 2
            continue
        }

        return $response
    }
}

if (-not (Test-Path -LiteralPath $skillsRoot)) {
    New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
}

foreach ($skill in $requiredSkills) {
    $skillFile = Join-Path (Join-Path $skillsRoot $skill) "SKILL.md"

    if ((Test-Path -LiteralPath $skillFile) -and -not $Force) {
        Add-Result -Name $skill -Passed $true -Detail "already installed"
        continue
    }

    $command = if (Test-Path -LiteralPath $skillFile) { "update" } else { "install" }
    $globalArgs = @("--workdir", $repoRoot, "--dir", (Split-Path -Leaf $skillsRoot), "--no-input")
    $commandArgs = if ($command -eq "update") {
        @("update", $skill)
    }
    else {
        @("install", $skill) + $(if ($ForceSuspicious) { @("--force") } else { @() })
    }
    $response = Invoke-ClawHubWithRetry -CommandArgs ($globalArgs + $commandArgs)
    $installed = Test-Path -LiteralPath $skillFile
    Add-Result -Name "$command $skill" -Passed ($response.ExitCode -eq 0 -and $installed) -Detail $(if ($installed) { "installed" } elseif ($response.Output) { $response.Output } else { "install failed" })

    Start-Sleep -Milliseconds 1250
}

$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

if (-not $SkipCheck) {
    & (Join-Path $PSScriptRoot "Invoke-AimsMarketSkillCheck.ps1") -SkillsRoot $skillsRoot -Skills $requiredSkills
    exit $LASTEXITCODE
}

exit 0
