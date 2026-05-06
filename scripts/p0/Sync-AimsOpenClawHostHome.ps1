param(
    [string]$EnvPath,
    [string]$HomeRoot,
    [string]$RuntimeConfigPath
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$envPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
$homeRoot = if ($HomeRoot) { $HomeRoot } else { Join-Path $repoRoot ".generated\openclaw-host-home" }
$runtimeConfigPath = if ($RuntimeConfigPath) { $RuntimeConfigPath } else { Join-Path $repoRoot ".generated\openclaw.runtime.json" }
$stateDir = Join-Path $homeRoot ".openclaw"
$exportRuntimeConfig = Join-Path $PSScriptRoot "Export-AimsRuntimeConfig.ps1"

if (-not (Test-Path -LiteralPath $exportRuntimeConfig)) {
    throw "Runtime config exporter not found: $exportRuntimeConfig"
}

& $exportRuntimeConfig -EnvPath $envPath -OutputPath $runtimeConfigPath | Out-Null
if (-not $?) {
    throw "Failed to export runtime config."
}

if (-not (Test-Path -LiteralPath $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}

$config = Get-Content -LiteralPath $runtimeConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

function Ensure-HostJunction {
    param(
        [string]$LinkPath,
        [string]$TargetPath
    )

    if (-not (Test-Path -LiteralPath $TargetPath)) {
        throw "Target path for junction does not exist: $TargetPath"
    }

    if (Test-Path -LiteralPath $LinkPath) {
        Remove-Item -LiteralPath $LinkPath -Recurse -Force -ErrorAction Stop
    }

    New-Item -ItemType Junction -Path $LinkPath -Target $TargetPath -Force | Out-Null
}

function Merge-ObjectProperties {
    param(
        [object]$Source,
        [object]$Target
    )

    if ($null -eq $Source -or $null -eq $Target) {
        return
    }

    foreach ($property in $Source.PSObject.Properties) {
        $exists = $false
        foreach ($targetProperty in $Target.PSObject.Properties) {
            if ($targetProperty.Name -eq $property.Name) {
                $exists = $true
                break
            }
        }

        if (-not $exists) {
            $Target | Add-Member -NotePropertyName $property.Name -NotePropertyValue $property.Value
        }
    }
}

function Test-ObjectHasProperty {
    param(
        [object]$InputObject,
        [string]$PropertyName
    )

    if ($null -eq $InputObject) {
        return $false
    }

    foreach ($property in $InputObject.PSObject.Properties) {
        if ($property.Name -eq $PropertyName) {
            return $true
        }
    }

    return $false
}

function New-HostModelAlias {
    param(
        [string]$ProviderName,
        [string]$ModelId
    )

    $alias = ("{0}-{1}" -f $ProviderName, $ModelId).ToLowerInvariant()
    $alias = $alias -replace "[^a-z0-9]+", "-"
    $alias = $alias.Trim("-")

    if ([string]::IsNullOrWhiteSpace($alias)) {
        return "model"
    }

    return $alias
}

function Ensure-SeedFile {
    param(
        [string]$DestinationPath,
        [string]$SourcePath,
        [string]$FallbackContent
    )

    if (Test-Path -LiteralPath $DestinationPath) {
        return
    }

    $destinationDir = Split-Path -Parent $DestinationPath
    if (-not (Test-Path -LiteralPath $destinationDir)) {
        New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
    }

    if (-not [string]::IsNullOrWhiteSpace($SourcePath) -and (Test-Path -LiteralPath $SourcePath)) {
        Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Force
        return
    }

    Set-Content -LiteralPath $DestinationPath -Value $FallbackContent -Encoding UTF8
}

$workspaceMap = [ordered]@{
    "workspace"           = Join-Path $repoRoot "workspace"
    "workspace-main"      = Join-Path $repoRoot "workspace-main"
    "workspace-ecommerce" = Join-Path $repoRoot "workspace-ecommerce"
    "workspace-social"    = Join-Path $repoRoot "workspace-social"
    "workspace-cs"        = Join-Path $repoRoot "workspace-cs"
    "workspace-office"    = Join-Path $repoRoot "workspace-office"
}

foreach ($entry in $workspaceMap.GetEnumerator()) {
    Ensure-HostJunction -LinkPath (Join-Path $stateDir $entry.Key) -TargetPath $entry.Value

    Ensure-SeedFile -DestinationPath (Join-Path $entry.Value "AGENTS.md") -SourcePath (Join-Path $repoRoot "AGENTS.md") -FallbackContent "# AIMS Workspace`r`n"
    Ensure-SeedFile -DestinationPath (Join-Path $entry.Value "SOUL.md") -SourcePath (Join-Path $repoRoot "SOUL.md") -FallbackContent "# AIMS Soul`r`n"
    Ensure-SeedFile -DestinationPath (Join-Path $entry.Value "TOOLS.md") -SourcePath (Join-Path $repoRoot "TOOLS.md") -FallbackContent "# Workspace Tools`r`n`r`n- Record workspace-specific commands and caveats here.`r`n"
    Ensure-SeedFile -DestinationPath (Join-Path $entry.Value "IDENTITY.md") -SourcePath "" -FallbackContent "# Identity`r`n`r`n- Name: AIMS`r`n- Theme: AI marketing system`r`n- Emoji: crab`r`n"
    Ensure-SeedFile -DestinationPath (Join-Path $entry.Value "USER.md") -SourcePath "" -FallbackContent "# User`r`n`r`n- Add workspace-specific operator notes here.`r`n"
}

Ensure-HostJunction -LinkPath (Join-Path $stateDir "skills") -TargetPath (Join-Path $repoRoot "skills")

$config.agents.defaults.workspace = (Join-Path $stateDir "workspace")
foreach ($agent in $config.agents.list) {
    switch ($agent.id) {
        "main" { $agent.workspace = Join-Path $stateDir "workspace-main" }
        "ecommerce" { $agent.workspace = Join-Path $stateDir "workspace-ecommerce" }
        "social-media" { $agent.workspace = Join-Path $stateDir "workspace-social" }
        "cs" { $agent.workspace = Join-Path $stateDir "workspace-cs" }
        "office" { $agent.workspace = Join-Path $stateDir "workspace-office" }
    }
}

if (($config.PSObject.Properties.Name -contains "identity") -and $null -ne $config.identity) {
    $identityTarget = $null

    foreach ($agent in $config.agents.list) {
        if ($agent.id -eq "main") {
            $identityTarget = $agent
            break
        }

        if (($null -eq $identityTarget) -and ($agent.PSObject.Properties.Name -contains "default") -and ($agent.default -eq $true)) {
            $identityTarget = $agent
        }
    }

    if (($null -eq $identityTarget) -and $config.agents.list.Count -gt 0) {
        $identityTarget = $config.agents.list[0]
    }

    if ($null -ne $identityTarget) {
        if (-not ($identityTarget.PSObject.Properties.Name -contains "identity")) {
            $identityTarget | Add-Member -NotePropertyName identity -NotePropertyValue $config.identity
        }
        elseif ($null -eq $identityTarget.identity) {
            $identityTarget.identity = $config.identity
        }
    }

    $config.PSObject.Properties.Remove("identity")
}

if (($config.agents.PSObject.Properties.Name -contains "defaults") -and
    ($config.agents.defaults.PSObject.Properties.Name -contains "tools") -and
    $null -ne $config.agents.defaults.tools) {
    if (-not ($config.PSObject.Properties.Name -contains "tools") -or $null -eq $config.tools) {
        $config | Add-Member -NotePropertyName tools -NotePropertyValue ([pscustomobject]@{})
    }

    Merge-ObjectProperties -Source $config.agents.defaults.tools -Target $config.tools
    $config.agents.defaults.PSObject.Properties.Remove("tools")
}

if (($config.PSObject.Properties.Name -contains "plugins") -and
    ($config.plugins.PSObject.Properties.Name -contains "entries")) {
    foreach ($pluginEntry in $config.plugins.entries.PSObject.Properties) {
        if ($pluginEntry.Value -and ($pluginEntry.Value.PSObject.Properties.Name -contains "env")) {
            $pluginEntry.Value.PSObject.Properties.Remove("env")
        }
    }
}

$pluginEntriesMap = [ordered]@{}
if (($config.PSObject.Properties.Name -contains "plugins") -and
    ($config.plugins.PSObject.Properties.Name -contains "entries") -and
    $null -ne $config.plugins.entries) {
    foreach ($pluginEntry in $config.plugins.entries.PSObject.Properties) {
        $enabled = $true
        if ($pluginEntry.Value -and (Test-ObjectHasProperty -InputObject $pluginEntry.Value -PropertyName "enabled")) {
            $enabled = [bool]$pluginEntry.Value.enabled
        }

        $pluginEntriesMap[$pluginEntry.Name] = [pscustomobject]@{
            enabled = $enabled
        }
    }
}

if ($pluginEntriesMap.Count -gt 0) {
    if (-not ($config.PSObject.Properties.Name -contains "plugins") -or $null -eq $config.plugins) {
        $config | Add-Member -NotePropertyName plugins -NotePropertyValue ([pscustomobject]@{})
    }

    if (Test-ObjectHasProperty -InputObject $config.plugins -PropertyName "entries") {
        $config.plugins.entries = [pscustomobject]$pluginEntriesMap
    }
    else {
        $config.plugins | Add-Member -NotePropertyName entries -NotePropertyValue ([pscustomobject]$pluginEntriesMap)
    }
}

if (($config.PSObject.Properties.Name -contains "models") -and
    ($config.models.PSObject.Properties.Name -contains "providers") -and
    $null -ne $config.models.providers) {
    if (-not ($config.agents.defaults.PSObject.Properties.Name -contains "models") -or $null -eq $config.agents.defaults.models) {
        $config.agents.defaults | Add-Member -NotePropertyName models -NotePropertyValue ([pscustomobject]@{})
    }

    foreach ($providerEntry in $config.models.providers.PSObject.Properties) {
        $providerName = [string]$providerEntry.Name
        $providerValue = $providerEntry.Value

        if (($null -eq $providerValue) -or (-not (Test-ObjectHasProperty -InputObject $providerValue -PropertyName "models"))) {
            continue
        }

        foreach ($model in @($providerValue.models)) {
            if ($null -eq $model -or -not (Test-ObjectHasProperty -InputObject $model -PropertyName "id")) {
                continue
            }

            $qualifiedModelId = ("{0}/{1}" -f $providerName, [string]$model.id)
            if (-not (Test-ObjectHasProperty -InputObject $config.agents.defaults.models -PropertyName $qualifiedModelId)) {
                $config.agents.defaults.models | Add-Member -NotePropertyName $qualifiedModelId -NotePropertyValue ([pscustomobject]@{
                    alias = (New-HostModelAlias -ProviderName $providerName -ModelId ([string]$model.id))
                })
            }
        }
    }

    $config.PSObject.Properties.Remove("models")
}

$unsupportedHostChannels = @("feishu", "wework", "dingtalk")
if ($config.PSObject.Properties.Name -contains "channels") {
    foreach ($channelName in $unsupportedHostChannels) {
        if ($config.channels.PSObject.Properties.Name -contains $channelName) {
            $config.channels.PSObject.Properties.Remove($channelName)
        }
    }

    foreach ($channelProperty in @($config.channels.PSObject.Properties)) {
        if ($channelProperty.Name -eq "defaults") {
            continue
        }

        if ($channelProperty.Value -and
            (Test-ObjectHasProperty -InputObject $channelProperty.Value -PropertyName "enabled") -and
            ($channelProperty.Value.enabled -eq $false)) {
            $config.channels.PSObject.Properties.Remove($channelProperty.Name)
        }
    }
}

if (($config.PSObject.Properties.Name -contains "bindings") -and $null -ne $config.bindings) {
    $config.bindings = @(
        $config.bindings | Where-Object {
            ($null -eq $_.match) -or
            ($null -eq $_.match.channel) -or
            ($unsupportedHostChannels -notcontains [string]$_.match.channel)
        }
    )
}

if ($config.PSObject.Properties.Name -contains "plugins") {
    if (-not (Test-ObjectHasProperty -InputObject $config.plugins -PropertyName "slots") -or $null -eq $config.plugins.slots) {
        $config.plugins | Add-Member -NotePropertyName slots -NotePropertyValue ([pscustomobject]@{})
    }

    if (-not (Test-ObjectHasProperty -InputObject $config.plugins.slots -PropertyName "memory")) {
        $config.plugins.slots | Add-Member -NotePropertyName memory -NotePropertyValue "none"
    }
    else {
        $config.plugins.slots.memory = "none"
    }
}

$hostConfigPath = Join-Path $stateDir "openclaw.json"
$config | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $hostConfigPath -Encoding UTF8

foreach ($name in @("SOUL.md", "AGENTS.md", "mcporter.json")) {
    $sourcePath = Join-Path $repoRoot $name
    if (Test-Path -LiteralPath $sourcePath) {
        Copy-Item -LiteralPath $sourcePath -Destination (Join-Path $stateDir $name) -Force
    }
}

$result = [pscustomobject]@{
    HomeRoot        = $homeRoot
    StateDir        = $stateDir
    RuntimeConfig   = $runtimeConfigPath
    HostConfig      = $hostConfigPath
    WorkspaceRoot   = (Join-Path $stateDir "workspace")
    MainWorkspace   = (Join-Path $stateDir "workspace-main")
    SkillsPath      = (Join-Path $stateDir "skills")
}

$result | ConvertTo-Json -Depth 10
