param(
    [string]$PortableRoot = "D:\openclaw\openclaw-portable-win-x64",
    [string]$EnvPath,
    [string]$HomeRoot,
    [string]$SourcePath,
    [string]$Timezone = "Asia/Shanghai",
    [int]$TimeoutSeconds = 300,
    [switch]$Apply,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$envPathInput = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
$homeRootInput = if ($HomeRoot) { $HomeRoot } else { Join-Path $repoRoot ".generated\openclaw-host-home" }
$sourcePathInput = if ($SourcePath) { $SourcePath } else { Join-Path $repoRoot "fixtures\cron\aims-legacy-cron-jobs.json" }

$envPath = [System.IO.Path]::GetFullPath($envPathInput)
$homeRoot = [System.IO.Path]::GetFullPath($homeRootInput)
$sourcePath = [System.IO.Path]::GetFullPath($sourcePathInput)
$portableRoot = [System.IO.Path]::GetFullPath($PortableRoot)
$syncScript = Join-Path $PSScriptRoot "Sync-AimsOpenClawHostHome.ps1"
$helperScript = Join-Path $PSScriptRoot "Invoke-AimsOpenClawHostCli.ps1"
$reportPath = Join-Path $repoRoot ".generated\legacy-cron-migration-report.json"

if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Legacy cron source not found: $sourcePath"
}

if (-not (Test-Path -LiteralPath $helperScript)) {
    throw "Host CLI helper not found: $helperScript"
}

if (-not (Test-Path -LiteralPath $syncScript)) {
    throw "Host sync script not found: $syncScript"
}

$envMap = Read-AimsDotEnv -Path $envPath
$legacyJobs = [object[]](Get-Content -LiteralPath $sourcePath -Raw -Encoding UTF8 | ConvertFrom-Json)

function Test-EnvKeysReady {
    param(
        [hashtable]$Map,
        [string[]]$Keys
    )

    $missing = New-Object System.Collections.Generic.List[string]
    foreach ($key in $Keys) {
        if (-not $Map.ContainsKey($key) -or [string]::IsNullOrWhiteSpace([string]$Map[$key])) {
            $missing.Add($key)
        }
    }

    return [pscustomobject]@{
        Ready = ($missing.Count -eq 0)
        Missing = @($missing)
    }
}

function Get-LegacyJobEnvRequirements {
    param([object]$Job)

    switch ([string]$Job.skill) {
        "rag-retrieval" { return @("MILVUS_HOST", "MILVUS_PORT") }
        "feishu-doc" { return @("FEISHU_BOT1_APP_ID", "FEISHU_BOT1_APP_SECRET") }
        default { return @() }
    }
}

function Convert-LegacyParamsToLines {
    param([object]$Params)

    $lines = New-Object System.Collections.Generic.List[string]
    if ($null -eq $Params) {
        $lines.Add("- none")
        return @($lines)
    }

    foreach ($property in $Params.PSObject.Properties) {
        $renderedValue = ""
        if ($null -eq $property.Value) {
            $renderedValue = "(null)"
        }
        elseif ($property.Value -is [string]) {
            $renderedValue = [string]$property.Value
        }
        elseif ($property.Value -is [System.Collections.IEnumerable]) {
            $renderedValue = (($property.Value | ForEach-Object { [string]$_ }) -join ", ")
        }
        else {
            $renderedValue = [string]$property.Value
        }

        $lines.Add("- $($property.Name): $renderedValue")
    }

    if ($lines.Count -eq 0) {
        $lines.Add("- none")
    }

    return @($lines)
}

function New-LegacyCronMessage {
    param([object]$Job)

    $paramsLines = Convert-LegacyParamsToLines -Params $Job.params

    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($line in @(
        "This is an AIMS scheduled task request.",
        "",
        "Task metadata:",
        "- legacy_job_id: $($Job.id)",
        "- display_name: $($Job.name)",
        "- target_agent: $($Job.agent)",
        "- preferred_skill: $($Job.skill)"
    )) {
        $lines.Add($line)
    }

    $lines.Add("- params:")
    foreach ($paramLine in $paramsLines) {
        $lines.Add([string]$paramLine)
    }

    foreach ($line in @(
        "",
        "Execution rules:",
        "1. Prefer the skill named $($Job.skill) when handling this task.",
        "2. If the current skill interface differs from the legacy params, do the smallest compatible mapping and mention it in the result.",
        "3. Do not perform unauthorized external publishing, deletion, refund, payment, repricing, or other high-risk write actions.",
        "4. If the task name or params imply publish or outbound actions, but the current skill only supports drafts or review, stop at draft output and mark manual review.",
        "5. Return a plain-text summary containing: status, action_taken, key_result, blockers, manual_review."
    )) {
        $lines.Add($line)
    }

    return (@($lines) -join "`n")
}

function Invoke-HostCli {
    param([string[]]$OpenClawArgs)

    $commandArgs = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $helperScript,
        "-PortableRoot", $portableRoot,
        "-EnvPath", $envPath,
        "-HomeRoot", $homeRoot,
        "-SkipSyncHome"
    ) + $OpenClawArgs

    $output = & powershell.exe @commandArgs 2>&1
    $exitCode = $LASTEXITCODE

    return [pscustomobject]@{
        ExitCode = $exitCode
        Text = (($output | ForEach-Object { [string]$_ }) -join "`n").Trim()
    }
}

function Invoke-HostCliWithRetry {
    param(
        [string[]]$OpenClawArgs,
        [int]$MaxAttempts = 5,
        [int]$DelaySeconds = 2
    )

    $result = $null
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt += 1) {
        $result = Invoke-HostCli -OpenClawArgs $OpenClawArgs
        if ($result.ExitCode -eq 0) {
            return $result
        }

        if ($attempt -lt $MaxAttempts) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    return $result
}

& $syncScript -EnvPath $envPath -HomeRoot $homeRoot | Out-Null

$listResult = Invoke-HostCliWithRetry -OpenClawArgs @("cron", "list", "--json")
if ($listResult.ExitCode -ne 0) {
    throw "Failed to list cron jobs.`n$listResult"
}

$existingPayload = $listResult.Text | ConvertFrom-Json
$existingJobs = @($existingPayload.jobs)
$existingByName = @{}
foreach ($job in $existingJobs) {
    $existingByName[[string]$job.name] = $job
}

$report = New-Object System.Collections.Generic.List[object]

foreach ($legacyJob in $legacyJobs) {
    $requirements = Get-LegacyJobEnvRequirements -Job $legacyJob
    $envStatus = Test-EnvKeysReady -Map $envMap -Keys $requirements
    $shouldEnable = [bool]$legacyJob.enabled -and $envStatus.Ready
    $message = New-LegacyCronMessage -Job $legacyJob
    $description = "Migrated from legacy openclaw.json cron job id=$($legacyJob.id); skill=$($legacyJob.skill)"
    $existing = $null
    if ($existingByName.ContainsKey([string]$legacyJob.name)) {
        $existing = $existingByName[[string]$legacyJob.name]
    }

    $entry = [ordered]@{
        legacyId = [string]$legacyJob.id
        name = [string]$legacyJob.name
        agent = [string]$legacyJob.agent
        skill = [string]$legacyJob.skill
        schedule = [string]$legacyJob.schedule
        requestedEnabled = [bool]$legacyJob.enabled
        migratedEnabled = $shouldEnable
        missingEnv = @($envStatus.Missing)
        action = "plan"
        notes = @()
    }

    if (-not $envStatus.Ready) {
        $entry.notes += ("Disabled during migration because env prerequisites are missing: {0}" -f ($envStatus.Missing -join ", "))
    }

    if ($null -ne $existing -and -not $Force) {
        $entry.action = "skip_existing"
        $entry.notes += "Existing cron job with the same name was found; rerun with -Force to replace it."
        $report.Add([pscustomobject]$entry)
        continue
    }

    if (-not $Apply) {
        $entry.action = if ($null -ne $existing) { "would_replace" } else { "would_create" }
        $report.Add([pscustomobject]$entry)
        continue
    }

    if ($null -ne $existing -and $Force) {
        $existingId = if ($existing.PSObject.Properties.Name -contains "jobId") { [string]$existing.jobId } else { [string]$existing.id }
        if (-not [string]::IsNullOrWhiteSpace($existingId)) {
            $rmResult = Invoke-HostCliWithRetry -OpenClawArgs @("cron", "rm", $existingId, "--json")
            if ($rmResult.ExitCode -ne 0) {
                $entry.action = "remove_failed"
                $entry.notes += "Failed to remove existing cron job."
                $entry.notes += $rmResult.Text
                $report.Add([pscustomobject]$entry)
                continue
            }
            $entry.notes += "Removed existing cron job before recreation."
        }
    }

    $addArgs = @(
        "cron", "add",
        "--json",
        "--name", [string]$legacyJob.name,
        "--description", $description,
        "--cron", [string]$legacyJob.schedule,
        "--tz", $Timezone,
        "--exact",
        "--session", "isolated",
        "--agent", [string]$legacyJob.agent,
        "--message", $message,
        "--no-deliver",
        "--timeout-seconds", [string]$TimeoutSeconds
    )

    if (-not $shouldEnable) {
        $addArgs += "--disabled"
    }

    $addResult = Invoke-HostCliWithRetry -OpenClawArgs $addArgs
    if ($addResult.ExitCode -ne 0) {
        $entry.action = "create_failed"
        $entry.notes += $addResult.Text
        $report.Add([pscustomobject]$entry)
        continue
    }

    $entry.action = if ($null -ne $existing) { "recreated" } else { "created" }
    try {
        $created = $addResult.Text | ConvertFrom-Json
        if ($created.PSObject.Properties.Name -contains "jobId") {
            $entry.jobId = [string]$created.jobId
        }
        elseif ($created.PSObject.Properties.Name -contains "id") {
            $entry.jobId = [string]$created.id
        }
    }
    catch {
        $entry.notes += "Created successfully, but the add response could not be parsed as JSON."
        if (-not [string]::IsNullOrWhiteSpace($addResult.Text)) {
            $entry.notes += $addResult.Text
        }
    }
    $report.Add([pscustomobject]$entry)
}

$reportDir = Split-Path -Parent $reportPath
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}

$reportItems = @($report.ToArray())
$reportJson = $reportItems | ConvertTo-Json -Depth 20
$reportJson | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Migration report written to $reportPath"
$reportJson
