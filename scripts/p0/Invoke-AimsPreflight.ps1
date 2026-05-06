param(
    [switch]$SkipCompose,
    [switch]$UseMirrorRegistry,
    [switch]$CheckOllama,
    [switch]$UseLocalLlm,
    [switch]$UseWsl,
    [switch]$CheckWsl,
    [string]$WslDistro
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$configPath = Join-Path $repoRoot "openclaw.json"
$composeFiles = Resolve-AimsComposeFiles -RepoRoot $repoRoot -UseMirrorRegistry:$UseMirrorRegistry -UseLocalLlm:$UseLocalLlm
$composePath = $composeFiles[0]
$localLlmComposePath = Get-AimsLocalLlmComposePath -RepoRoot $repoRoot
$envExamplePath = Join-Path $repoRoot ".env.example"
$mcpPath = Join-Path $repoRoot "mcporter.json"
$soulPath = Join-Path $repoRoot "SOUL.md"
$agentsPath = Join-Path $repoRoot "AGENTS.md"
$initSqlPath = Join-Path $repoRoot "init.sql"
$ollamaCheckScript = Join-Path $PSScriptRoot "Invoke-AimsOllamaCheck.ps1"
$localLlmHealthScript = Join-Path $PSScriptRoot "Invoke-AimsLocalLlmHealth.ps1"
$localStorageScript = Join-Path $PSScriptRoot "Initialize-AimsLocalStorage.ps1"
$dependencyPolicyScript = Join-Path $PSScriptRoot "Invoke-AimsDependencyPolicyCheck.ps1"
$wslDockerCheckScript = Join-Path $PSScriptRoot "Invoke-AimsWslDockerCheck.ps1"
$wslComposeScript = Join-Path $PSScriptRoot "Start-AimsWslCompose.ps1"

$results = New-Object System.Collections.Generic.List[object]
$warnings = New-Object System.Collections.Generic.List[string]
$effectiveCheckWsl = ($CheckWsl -or $UseWsl)
$agentModelProviders = @()
$agentModelRefs = @()
$modelProviderApiKeys = @{}
$usesOllamaModels = $false
$usesEnvDrivenModels = $false

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

function Test-File {
    param(
        [string]$Path,
        [string]$Name
    )

    $exists = Test-Path -LiteralPath $Path
    Add-Result -Name $Name -Passed $exists -Detail $Path
    return $exists
}

function Get-EnvPlaceholderKey {
    param(
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }

    $match = [regex]::Match($Value, '^\$\{([^}]+)\}$')
    if ($match.Success) {
        return $match.Groups[1].Value
    }

    return ""
}

function Get-ModelProviderId {
    param(
        [string]$ModelRef
    )

    if ([string]::IsNullOrWhiteSpace($ModelRef)) {
        return ""
    }

    if ($ModelRef -match '^\$\{') {
        return "env"
    }

    $parts = $ModelRef -split "/", 2
    if ($parts.Count -lt 2 -or [string]::IsNullOrWhiteSpace($parts[0])) {
        return ""
    }

    return $parts[0]
}

function Test-EnvHasValue {
    param(
        [hashtable]$Map,
        [string]$Key
    )

    return ($null -ne $Map -and $Map.ContainsKey($Key) -and -not [string]::IsNullOrWhiteSpace([string]$Map[$Key]))
}

$hasConfig = Test-File -Path $configPath -Name "openclaw.json exists"
$hasCompose = Test-File -Path $composePath -Name "docker-compose.yml exists"
if ($UseLocalLlm) {
    Test-File -Path $localLlmComposePath -Name "docker-compose.local-llm.yml exists" | Out-Null
}
$hasEnvExample = Test-File -Path $envExamplePath -Name ".env.example exists"
$hasMcp = Test-File -Path $mcpPath -Name "mcporter.json exists"
$hasSoul = Test-File -Path $soulPath -Name "SOUL.md exists"
$hasAgents = Test-File -Path $agentsPath -Name "AGENTS.md exists"
$hasInitSql = Test-File -Path $initSqlPath -Name "init.sql exists"

if ($hasConfig) {
    $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json

    Add-Result -Name "gateway.mode" -Passed ($config.gateway.mode -eq "local") -Detail "Expected local"
    Add-Result -Name "gateway.bind" -Passed ($config.gateway.bind -in @("lan", "custom")) -Detail "Docker port-mapping needs lan/custom inside the container"
    Add-Result -Name "gateway.auth.mode" -Passed ($config.gateway.auth.mode -eq "token") -Detail "Expected token auth"
    Add-Result -Name "session.dmScope" -Passed ($config.session.dmScope -eq "per-channel-peer") -Detail "Expected per-channel-peer"
    Add-Result -Name "agents.defaults.sandbox.mode" -Passed ($config.agents.defaults.sandbox.mode -eq "non-main") -Detail "Expected non-main"
    Add-Result -Name "agents.defaults.tools.fs.workspaceOnly" -Passed ($config.agents.defaults.tools.fs.workspaceOnly -eq $true) -Detail "Expected workspace-only file access"
    Add-Result -Name "agents.defaults.tools.elevated.enabled" -Passed ($config.agents.defaults.tools.elevated.enabled -eq $false) -Detail "Elevated tools should stay disabled"

    $agentIds = @($config.agents.list | ForEach-Object { $_.id })
    $requiredAgents = @("main", "ecommerce", "social-media", "cs", "office")
    $missingAgents = @($requiredAgents | Where-Object { $_ -notin $agentIds })
    Add-Result -Name "agent roster" -Passed ($missingAgents.Count -eq 0) -Detail ("Missing: " + ($(if ($missingAgents.Count) { $missingAgents -join ", " } else { "none" })))

    $bindingHasLegacyGroup = @($config.bindings | Where-Object {
        $_.match -and $_.match.PSObject.Properties.Name -contains "group"
    }).Count -gt 0
    Add-Result -Name "bindings use current match fields" -Passed (-not $bindingHasLegacyGroup) -Detail "Expected accountId / peer-based routing, not legacy group name matching"

    $providerIds = @()
    if (($config.PSObject.Properties.Name -contains "models") -and
        ($config.models.PSObject.Properties.Name -contains "providers") -and
        $null -ne $config.models.providers) {
        $providerIds = @($config.models.providers.PSObject.Properties.Name)
        foreach ($providerProperty in $config.models.providers.PSObject.Properties) {
            $envKey = ""
            if ($providerProperty.Value -and ($providerProperty.Value.PSObject.Properties.Name -contains "apiKey")) {
                $envKey = Get-EnvPlaceholderKey -Value ([string]$providerProperty.Value.apiKey)
            }

            if (-not [string]::IsNullOrWhiteSpace($envKey)) {
                $modelProviderApiKeys[$providerProperty.Name] = $envKey
            }
        }
    }

    $primaryModel = [string]$config.agents.defaults.model.primary
    $fallbackModels = @($config.agents.defaults.model.fallbacks | Where-Object {
        $null -ne $_ -and -not [string]::IsNullOrWhiteSpace([string]$_)
    })
    $agentModelRefs = @($primaryModel) + $fallbackModels
    $resolvedModelProviders = @($agentModelRefs | ForEach-Object {
        Get-ModelProviderId -ModelRef ([string]$_)
    })
    $agentModelProviders = @($resolvedModelProviders | Where-Object { $_ -notin @("", "env") } | Select-Object -Unique)
    $usesEnvDrivenModels = @($resolvedModelProviders | Where-Object { $_ -eq "env" }).Count -gt 0
    $usesOllamaModels = @($resolvedModelProviders | Where-Object { $_ -eq "ollama" }).Count -gt 0

    $missingModelProviders = @($agentModelProviders | Where-Object { $_ -notin $providerIds })
    Add-Result -Name "agent model providers declared" -Passed ($missingModelProviders.Count -eq 0) -Detail ("Models: " + ($agentModelRefs -join ", ") + "; missing providers: " + $(if ($missingModelProviders.Count) { $missingModelProviders -join ", " } else { "none" }))

    $hasOllamaProvider = (
        ($providerIds -contains "ollama") -and
        ($config.models.providers.ollama.api -eq "ollama")
    )
    Add-Result -Name "ollama provider configured when referenced" -Passed ((-not $usesOllamaModels) -or $hasOllamaProvider) -Detail $(if ($usesOllamaModels) { "Ollama-backed agent models require models.providers.ollama.api = ollama" } else { "Agent models do not currently reference ollama/*" })

    $skills = @()
    if (($config.PSObject.Properties.Name -contains "skills") -and
        ($config.skills.PSObject.Properties.Name -contains "entries") -and
        $null -ne $config.skills.entries) {
        $skills = @($config.skills.entries.PSObject.Properties.Name)
    }
    $requiredSkills = @("skill-vetter", "skill-manager", "find-skills-skill", "agent-health-optimizer")
    $missingSkills = @($requiredSkills | Where-Object { $_ -notin $skills })
    Add-Result -Name "skills config declared" -Passed ($missingSkills.Count -eq 0) -Detail ("Missing: " + ($(if ($missingSkills.Count) { $missingSkills -join ", " } else { "none" })))

    if (-not $config.channels.feishu.defaultAccount) {
        $warnings.Add("channels.feishu.defaultAccount is empty; outbound routing may become ambiguous.")
    }

    if ($usesEnvDrivenModels) {
        $warnings.Add("agents.defaults.model uses environment placeholders. Make sure the resolved provider/model values are declared in models.providers.")
    }
}

if ($hasEnvExample) {
    $envExample = Get-Content -LiteralPath $envExamplePath
    $requiredEnvKeys = @(
        "DEEPSEEK_API_KEY",
        "MOONSHOT_API_KEY",
        "ZHIPU_API_KEY",
        "OLLAMA_API_KEY",
        "AIMS_DOCKER_OLLAMA_ENDPOINT",
        "AIMS_HOST_SHARED_OLLAMA_ENDPOINT",
        "AIMS_OPENCLAW_IMAGE",
        "AIMS_OLLAMA_IMAGE",
        "AIMS_PYTHON_IMAGE",
        "AIMS_OLLAMA_HOST_PORT",
        "AIMS_TOOLS_ROOT",
        "AIMS_LOCAL_STORAGE_ROOT",
        "AIMS_OLLAMA_DATA_DIR",
        "AIMS_LOCAL_MODEL_CACHE_DIR",
        "AIMS_MYSQL_DATA_DIR",
        "AIMS_REDIS_DATA_DIR",
        "AIMS_MINIO_DATA_DIR",
        "AIMS_MILVUS_DATA_DIR",
        "AIMS_QDRANT_DATA_DIR",
        "AIMS_CLAWHUB_CACHE_DIR",
        "AIMS_NPM_CACHE_DIR",
        "AIMS_PIP_CACHE_DIR",
        "AIMS_LOCAL_MODEL_PULL_LIST",
        "AIMS_LOCAL_OPTIONAL_MODEL_PULL_LIST",
        "AIMS_LOCAL_RERANK_REPO",
        "AIMS_LOCAL_WHISPER_REPO",
        "LLM_PRIMARY_MODEL",
        "LLM_VLLM_ENDPOINT",
        "LLM_TRITON_ENDPOINT",
        "LLM_OLLAMA_ENDPOINT",
        "LLM_MULTIMODAL_MODEL",
        "LLM_RERANK_MODEL",
        "AIMS_GATEWAY_TOKEN",
        "AIMS_OPENCLAW_CONFIG_PATH",
        "FEISHU_BOT1_APP_ID",
        "FEISHU_BOT2_APP_ID",
        "FEISHU_OFFICE_GROUP_ID",
        "MYSQL_ROOT_PASSWORD",
        "MYSQL_PASSWORD",
        "MINIO_ROOT_USER",
        "MINIO_ROOT_PASSWORD"
    )
    $missingEnvKeys = @($requiredEnvKeys | Where-Object {
        $key = $_
        -not ($envExample | Where-Object { $_ -match "^$key=" })
    })
    Add-Result -Name ".env.example keys" -Passed ($missingEnvKeys.Count -eq 0) -Detail ("Missing: " + ($(if ($missingEnvKeys.Count) { $missingEnvKeys -join ", " } else { "none" })))

    $envPath = Join-Path $repoRoot ".env"
    if (-not (Test-Path -LiteralPath $envPath)) {
        $warnings.Add(".env is missing. Copy .env.example to .env before starting Docker services.")
    }
    else {
        $envMap = Read-AimsDotEnv -Path $envPath
        foreach ($providerId in $agentModelProviders) {
            if ($modelProviderApiKeys.ContainsKey($providerId)) {
                $envKey = [string]$modelProviderApiKeys[$providerId]
                if (-not (Test-EnvHasValue -Map $envMap -Key $envKey)) {
                    $warnings.Add("$envKey is missing in .env. Provider '$providerId' is referenced by agents.defaults.model, so model requests will fail until this credential is set.")
                }
            }
        }

        $expectsLocalLlm = ($UseLocalLlm -or $CheckOllama -or $usesOllamaModels)
        if ($expectsLocalLlm) {
            if (-not (Test-EnvHasValue -Map $envMap -Key "OLLAMA_API_KEY")) {
                $warnings.Add("OLLAMA_API_KEY is missing in .env. OpenClaw will not be able to use local Ollama models.")
            }

            if (-not (Test-EnvHasValue -Map $envMap -Key "LLM_PRIMARY_MODEL")) {
                $warnings.Add("LLM_PRIMARY_MODEL is missing in .env. Set it to the Ollama text model you actually have installed.")
            }

            if (-not (Test-EnvHasValue -Map $envMap -Key "AIMS_DOCKER_OLLAMA_ENDPOINT")) {
                $warnings.Add("AIMS_DOCKER_OLLAMA_ENDPOINT is missing in .env. Dockerized OpenClaw should point to http://ollama:11434 for the compose-managed local LLM stack, or http://host.docker.internal:11434 for a host-side Ollama instance.")
            }
            elseif ($envMap["AIMS_DOCKER_OLLAMA_ENDPOINT"] -match "^http://(localhost|127\.0\.0\.1)") {
                $warnings.Add("AIMS_DOCKER_OLLAMA_ENDPOINT points to localhost. That address is wrong inside the OpenClaw container. Use http://ollama:11434 for the compose-managed local LLM stack, or http://host.docker.internal:11434 for a host-side Ollama instance.")
            }

            if (-not (Test-EnvHasValue -Map $envMap -Key "AIMS_HOST_SHARED_OLLAMA_ENDPOINT")) {
                $warnings.Add("AIMS_HOST_SHARED_OLLAMA_ENDPOINT is missing in .env. Shared-host Ollama fallback should normally point to http://host.docker.internal:11434 on Docker Desktop.")
            }

            $ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
            if ($null -eq $ollamaCommand) {
                $warnings.Add("Ollama CLI is not on PATH. This is acceptable if you use the Docker-managed local LLM stack; otherwise install Ollama or point the gateway to a reachable Ollama endpoint.")
            }

            if ($envMap.ContainsKey("LLM_OLLAMA_ENDPOINT") -and
                ($envMap["LLM_OLLAMA_ENDPOINT"] -eq "http://localhost:11434" -or $envMap["LLM_OLLAMA_ENDPOINT"] -eq "http://127.0.0.1:11434")) {
                $warnings.Add("LLM_OLLAMA_ENDPOINT points to localhost. That is correct for host-mode OpenClaw and host-side health probes. Dockerized OpenClaw uses AIMS_DOCKER_OLLAMA_ENDPOINT instead, which should normally be http://ollama:11434 for the compose-managed local LLM stack.")
            }
        }

        if ($envMap.ContainsKey("AIMS_OPENCLAW_CONFIG_PATH")) {
            $runtimeConfigPath = Join-Path $repoRoot ($envMap["AIMS_OPENCLAW_CONFIG_PATH"] -replace '^\./', '')
            if (-not (Test-Path -LiteralPath $runtimeConfigPath)) {
                $warnings.Add("AIMS_OPENCLAW_CONFIG_PATH points to a missing file: $runtimeConfigPath. Re-run scripts/p0/Export-AimsRuntimeConfig.ps1.")
            }
        }

        if (-not (Test-Path -LiteralPath $localStorageScript)) {
            Add-Result -Name "local storage script exists" -Passed $false -Detail $localStorageScript
        }
        else {
            $storageRaw = & $localStorageScript -EnvPath $envPath -AsJson 2>&1
            $storageText = ($storageRaw | Out-String).Trim()
            $storageJsonStart = $storageText.IndexOf("{")

            if ($LASTEXITCODE -ne 0 -or $storageJsonStart -lt 0) {
                Add-Result -Name "local storage policy" -Passed $false -Detail $storageText
            }
            else {
                $storageCheck = $storageText.Substring($storageJsonStart) | ConvertFrom-Json
                foreach ($item in @($storageCheck.results)) {
                    Add-Result -Name ("local storage: " + $item.Name) -Passed ($item.Status -eq "PASS") -Detail ([string]$item.Detail)
                }
            }
        }
    }
}

if ($hasMcp) {
    $mcpConfig = Get-Content -LiteralPath $mcpPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $mcpNames = @($mcpConfig.mcpServers.PSObject.Properties.Name)
    $requiredMcp = @("mysql-mcp", "redis-mcp", "milvus-mcp", "qdrant-mcp")
    $missingMcp = @($requiredMcp | Where-Object { $_ -notin $mcpNames })
    Add-Result -Name "core MCP servers declared" -Passed ($missingMcp.Count -eq 0) -Detail ("Missing: " + ($(if ($missingMcp.Count) { $missingMcp -join ", " } else { "none" })))
}

if ($hasSoul) {
    $soulContent = Get-Content -LiteralPath $soulPath -Raw
    $requiredSoulSections = @("## 身份", "## 核心原则", "## 能力范围", "## 输出规范", "## 安全红线")
    $missingSoulSections = @($requiredSoulSections | Where-Object { $soulContent -notmatch [regex]::Escape($_) })
    Add-Result -Name "SOUL.md sections" -Passed ($missingSoulSections.Count -eq 0) -Detail ("Missing: " + ($(if ($missingSoulSections.Count) { $missingSoulSections -join ", " } else { "none" })))
}

if ($hasAgents) {
    $agentsContent = Get-Content -LiteralPath $agentsPath -Raw
    $requiredAgentSections = @("## main", "## ecommerce", "## social-media", "## cs", "## office")
    $missingAgentSections = @($requiredAgentSections | Where-Object { $agentsContent -notmatch [regex]::Escape($_) })
    Add-Result -Name "AGENTS.md sections" -Passed ($missingAgentSections.Count -eq 0) -Detail ("Missing: " + ($(if ($missingAgentSections.Count) { $missingAgentSections -join ", " } else { "none" })))
}

if ($hasInitSql) {
    $initSql = Get-Content -LiteralPath $initSqlPath -Raw
    $requiredTables = @("sessions", "users", "products", "orders", "reviews", "contents", "cron_jobs", "knowledge_docs")
    $missingTables = @($requiredTables | Where-Object { $initSql -notmatch ("CREATE TABLE IF NOT EXISTS\s+" + [regex]::Escape($_)) })
    $hasCronSeed = $initSql -match "INSERT INTO cron_jobs"
    Add-Result -Name "init.sql baseline schema" -Passed ($missingTables.Count -eq 0 -and $hasCronSeed) -Detail ("Missing tables: " + ($(if ($missingTables.Count) { $missingTables -join ", " } else { "none" })) + "; cron seed: " + $(if ($hasCronSeed) { "present" } else { "missing" }))
}

if (-not (Test-Path -LiteralPath $dependencyPolicyScript)) {
    Add-Result -Name "dependency policy script exists" -Passed $false -Detail $dependencyPolicyScript
}
else {
    $dependencyPolicyRaw = & $dependencyPolicyScript -EnvPath (Join-Path $repoRoot ".env") 2>&1
    Add-Result -Name "dependency policy check" -Passed ($LASTEXITCODE -eq 0) -Detail ($(if ($LASTEXITCODE -eq 0) { "ok" } else { ($dependencyPolicyRaw | Out-String).Trim() }))
}

if ($effectiveCheckWsl) {
    if (-not (Test-Path -LiteralPath $wslDockerCheckScript)) {
        Add-Result -Name "wsl docker check script exists" -Passed $false -Detail $wslDockerCheckScript
    }
    else {
        $wslCheckParams = @{
            AsJson = $true
        }
        if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
            $wslCheckParams["Distro"] = $WslDistro
        }

        $wslCheckRaw = & $wslDockerCheckScript @wslCheckParams 2>&1
        $wslCheckText = ($wslCheckRaw | Out-String).Trim()
        $wslCheckJsonStart = $wslCheckText.IndexOf("{")

        if ($wslCheckJsonStart -lt 0) {
            Add-Result -Name "wsl docker check output" -Passed $false -Detail $wslCheckText
        }
        else {
            $wslCheck = $wslCheckText.Substring($wslCheckJsonStart) | ConvertFrom-Json
            foreach ($item in @($wslCheck.results)) {
                Add-Result -Name ("wsl: " + $item.Name) -Passed ($item.Status -eq "PASS") -Detail ([string]$item.Detail)
            }
        }
    }

    if (-not (Test-Path -LiteralPath $wslComposeScript)) {
        Add-Result -Name "wsl compose script exists" -Passed $false -Detail $wslComposeScript
    }
    else {
        $wslDryRunParams = @{
            DryRun       = $true
            StartGateway = $true
        }

        if ($UseLocalLlm) {
            $wslDryRunParams["UseLocalLlm"] = $true
        }

        if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
            $wslDryRunParams["Distro"] = $WslDistro
        }

        $wslDryRunRaw = & $wslComposeScript @wslDryRunParams 2>&1
        Add-Result -Name "wsl compose dry run" -Passed ($LASTEXITCODE -eq 0) -Detail ($(if ($LASTEXITCODE -eq 0) { "ok" } else { ($wslDryRunRaw | Out-String).Trim() }))
    }
}

if ($CheckOllama) {
    if ($UseLocalLlm) {
        if (-not (Test-Path -LiteralPath $localLlmHealthScript)) {
            Add-Result -Name "local llm health script exists" -Passed $false -Detail $localLlmHealthScript
        }
        else {
            $localLlmCheckParams = @{
                AsJson         = $true
                TimeoutSeconds = 15
            }
            if ($UseWsl) {
                $localLlmCheckParams["UseWsl"] = $true
                if (-not [string]::IsNullOrWhiteSpace($WslDistro)) {
                    $localLlmCheckParams["WslDistro"] = $WslDistro
                }
            }

            $localLlmCheckRaw = & $localLlmHealthScript @localLlmCheckParams 2>&1
            $localLlmCheckText = ($localLlmCheckRaw | Out-String).Trim()
            $localLlmJsonStart = $localLlmCheckText.IndexOf("{")

            if ($localLlmJsonStart -lt 0) {
                Add-Result -Name "local llm check output" -Passed $false -Detail $localLlmCheckText
            }
            else {
                $localLlmCheck = $localLlmCheckText.Substring($localLlmJsonStart) | ConvertFrom-Json
                foreach ($item in @($localLlmCheck.results)) {
                    Add-Result -Name ("local llm: " + $item.Name) -Passed ($item.Status -eq "PASS") -Detail ([string]$item.Detail)
                }
            }
        }
    }
    elseif (-not (Test-Path -LiteralPath $ollamaCheckScript)) {
        Add-Result -Name "ollama check script exists" -Passed $false -Detail $ollamaCheckScript
    }
    else {
        $ollamaCheckRaw = & $ollamaCheckScript -EnvPath (Join-Path $repoRoot ".env") -AsJson 2>&1
        $ollamaCheckText = ($ollamaCheckRaw | Out-String).Trim()
        $ollamaJsonStart = $ollamaCheckText.IndexOf("{")

        if ($ollamaJsonStart -lt 0) {
            Add-Result -Name "ollama check output" -Passed $false -Detail $ollamaCheckText
        }
        else {
            $ollamaCheck = $ollamaCheckText.Substring($ollamaJsonStart) | ConvertFrom-Json
            foreach ($item in @($ollamaCheck.results)) {
                Add-Result -Name ("ollama: " + $item.Name) -Passed ($item.Status -eq "PASS") -Detail ([string]$item.Detail)
            }
        }
    }
}

if (-not $SkipCompose -and $hasCompose) {
    if ($UseWsl) {
        Add-Result -Name "docker compose config" -Passed $true -Detail "Skipped Windows docker compose config because -UseWsl relies on WSL Docker checks and WSL compose dry-run."
    }
    else {
        $composeCommand = New-AimsComposeCommandArguments -ComposeFiles $composeFiles -AdditionalArgs @("config")
        $composeOutput = & docker @composeCommand 2>&1
        Add-Result -Name "docker compose config" -Passed ($LASTEXITCODE -eq 0) -Detail ($(if ($LASTEXITCODE -eq 0) { "compose parsed successfully" } else { ($composeOutput | Out-String).Trim() }))
    }
}

$results | Format-Table -AutoSize

if ($warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "Warnings:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host ("- " + $warning) -ForegroundColor Yellow
    }
}

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
