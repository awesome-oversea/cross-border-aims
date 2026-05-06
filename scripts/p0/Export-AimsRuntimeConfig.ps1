param(
    [string]$EnvPath,
    [string]$OutputPath,
    [switch]$Activate
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$configPath = Join-Path $repoRoot "openclaw.json"
$envPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
$outputPath = if ($OutputPath) { $OutputPath } else { Join-Path $repoRoot ".generated/openclaw.runtime.json" }
$legacyCronJobsPath = Join-Path $repoRoot ".generated/openclaw.legacy-cron-jobs.json"

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "openclaw.json not found: $configPath"
}

$envMap = Read-AimsDotEnv -Path $envPath
$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$changes = New-Object System.Collections.Generic.List[string]
$legacyCronJobs = @()
$legacySkillPathKeys = New-Object System.Collections.Generic.List[string]

function Test-HasValues {
    param(
        [hashtable]$Map,
        [string[]]$Keys
    )

    foreach ($key in $Keys) {
        if (-not $Map.ContainsKey($key)) {
            return $false
        }

        if ([string]::IsNullOrWhiteSpace($Map[$key])) {
            return $false
        }
    }

    return $true
}

function Disable-TopLevelChannel {
    param(
        [object]$Channels,
        [string]$ChannelName,
        [string[]]$RequiredKeys
    )

    if (-not ($Channels.PSObject.Properties.Name -contains $ChannelName)) {
        return
    }

    if (-not (Test-HasValues -Map $envMap -Keys $RequiredKeys)) {
        $Channels.$ChannelName.enabled = $false
        $changes.Add("Disabled channel '$ChannelName' because required env keys are missing: $($RequiredKeys -join ', ')")
    }
}

if ($config.channels.PSObject.Properties.Name -contains "feishu") {
    $enabledAccounts = New-Object System.Collections.Generic.List[string]
    foreach ($accountProp in $config.channels.feishu.accounts.PSObject.Properties) {
        $requiredKeys = @()

        if ($accountProp.Value.appId -match '^\$\{([^}]+)\}$') {
            $requiredKeys += $Matches[1]
        }
        if ($accountProp.Value.appSecret -match '^\$\{([^}]+)\}$') {
            $requiredKeys += $Matches[1]
        }

        if ($requiredKeys.Count -eq 0 -or (Test-HasValues -Map $envMap -Keys $requiredKeys)) {
            $enabledAccounts.Add($accountProp.Name)
        }
        else {
            $accountProp.Value.enabled = $false
            $changes.Add("Disabled Feishu account '$($accountProp.Name)' because required env keys are missing: $($requiredKeys -join ', ')")
        }
    }

    if ($enabledAccounts.Count -eq 0) {
        $config.channels.feishu.enabled = $false
        $changes.Add("Disabled channel 'feishu' because no enabled account has complete credentials.")
    }
    elseif ($config.channels.feishu.defaultAccount -notin $enabledAccounts) {
        $config.channels.feishu.defaultAccount = $enabledAccounts[0]
        $changes.Add("Updated Feishu defaultAccount to '$($enabledAccounts[0])' to match the available runtime credentials.")
    }
}

Disable-TopLevelChannel -Channels $config.channels -ChannelName "wework" -RequiredKeys @("WEWORK_CORP_ID", "WEWORK_AGENT_SECRET")
Disable-TopLevelChannel -Channels $config.channels -ChannelName "dingtalk" -RequiredKeys @("DINGTALK_APP_KEY", "DINGTALK_APP_SECRET")
Disable-TopLevelChannel -Channels $config.channels -ChannelName "telegram" -RequiredKeys @("TELEGRAM_BOT_TOKEN")
Disable-TopLevelChannel -Channels $config.channels -ChannelName "whatsapp" -RequiredKeys @("WHATSAPP_ALLOW_FROM")
Disable-TopLevelChannel -Channels $config.channels -ChannelName "discord" -RequiredKeys @("DISCORD_TOKEN")

$skillEnvRequirements = @{
    "brave-search"    = @("BRAVE_API_KEY")
    "tavily-search"   = @("TAVILY_API_KEY")
    "nano-banana-pro" = @("GEMINI_API_KEY")
    "feishu-doc"      = @("FEISHU_BOT1_APP_ID", "FEISHU_BOT1_APP_SECRET")
    "rag-retrieval"   = @("MILVUS_HOST", "MILVUS_PORT")
}

if (($config.PSObject.Properties.Name -contains "skills") -and
    ($config.skills.PSObject.Properties.Name -contains "entries") -and
    $null -ne $config.skills.entries) {
    foreach ($skillId in $skillEnvRequirements.Keys) {
        if ($config.skills.entries.PSObject.Properties.Name -contains $skillId) {
            if (-not (Test-HasValues -Map $envMap -Keys $skillEnvRequirements[$skillId])) {
                $config.skills.entries.$skillId.enabled = $false
                $changes.Add("Disabled skill '$skillId' because required env keys are missing: $($skillEnvRequirements[$skillId] -join ', ')")
            }
        }
    }

    foreach ($skillEntry in $config.skills.entries.PSObject.Properties) {
        if ($skillEntry.Value -and ($skillEntry.Value.PSObject.Properties.Name -contains "path")) {
            $skillEntry.Value.PSObject.Properties.Remove("path")
            $legacySkillPathKeys.Add($skillEntry.Name)
        }

        if ($skillEntry.Value -and ($skillEntry.Value.PSObject.Properties.Name -contains "env") -and $null -ne $skillEntry.Value.env) {
            $removedEnvKeys = New-Object System.Collections.Generic.List[string]
            foreach ($envProperty in @($skillEntry.Value.env.PSObject.Properties)) {
                $envValue = [string]$envProperty.Value
                if ($envValue -match '^\$\{([^}]+)\}$') {
                    $envKey = $Matches[1]
                    if (-not (Test-HasValues -Map $envMap -Keys @($envKey))) {
                        $skillEntry.Value.env.PSObject.Properties.Remove($envProperty.Name)
                        $removedEnvKeys.Add($envProperty.Name)
                    }
                }
            }

            if ($removedEnvKeys.Count -gt 0) {
                $changes.Add("Removed unresolved env placeholders from skill '$($skillEntry.Name)': $($removedEnvKeys -join ', ')")
            }

            if (@($skillEntry.Value.env.PSObject.Properties).Count -eq 0) {
                $skillEntry.Value.PSObject.Properties.Remove("env")
            }
        }
    }
}

if ($legacySkillPathKeys.Count -gt 0) {
    $changes.Add("Removed legacy skills.entries.*.path keys from runtime config; skills are loaded from the synced ~/.openclaw/skills and workspace skills directories.")
}

if (($config.PSObject.Properties.Name -contains "cron") -and
    ($config.cron.PSObject.Properties.Name -contains "jobs") -and
    $null -ne $config.cron.jobs) {
    $legacyCronJobs = @($config.cron.jobs)
    $config.cron.PSObject.Properties.Remove("jobs")
    $changes.Add("Removed legacy config key 'cron.jobs' from runtime config; exported definitions to $legacyCronJobsPath for CLI-based migration.")
}

$outputDir = Split-Path -Parent $outputPath
if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

if ($legacyCronJobs.Count -gt 0) {
    $legacyCronJson = $legacyCronJobs | ConvertTo-Json -Depth 100
    Set-Content -LiteralPath $legacyCronJobsPath -Value $legacyCronJson -Encoding UTF8
}

$json = $config | ConvertTo-Json -Depth 100
Set-Content -LiteralPath $outputPath -Value $json -Encoding UTF8

if ($Activate) {
    Set-AimsDotEnvValues -Path $envPath -Values @{ AIMS_OPENCLAW_CONFIG_PATH = "./.generated/openclaw.runtime.json" }
}

Write-Host "Runtime config written to $outputPath"
if ($Activate) {
    Write-Host "AIMS_OPENCLAW_CONFIG_PATH updated in $envPath"
}

if ($changes.Count -gt 0) {
    Write-Host ""
    Write-Host "Runtime adjustments:"
    foreach ($change in $changes) {
        Write-Host ("- " + $change)
    }
}
else {
    Write-Host "No runtime adjustments were needed."
}
