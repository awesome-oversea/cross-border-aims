param(
    [switch]$StartServices,
    [switch]$UseMirrorRegistry,
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$composeFiles = Resolve-AimsComposeFiles -RepoRoot $repoRoot -UseMirrorRegistry:$UseMirrorRegistry
$envPath = Join-Path $repoRoot ".env"
$envMap = Read-AimsDotEnv -Path $envPath
$minioApiPort = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_MINIO_API_PORT" -Default "19000"
$milvusHealthPort = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_MILVUS_HEALTH_PORT" -Default "19091"
$qdrantHttpPort = Get-AimsEnvValueOrDefault -Map $envMap -Key "AIMS_QDRANT_HTTP_PORT" -Default "16333"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw ".env is missing. Run scripts/p0/Initialize-AimsEnv.ps1 first."
}

$results = New-Object System.Collections.Generic.List[object]

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

function Invoke-Compose {
    param(
        [string[]]$ComposeArgs
    )

    $composeCommand = New-AimsComposeCommandArguments -ComposeFiles $composeFiles -AdditionalArgs $ComposeArgs
    $output = & docker @composeCommand 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output   = ($output | Out-String).Trim()
    }
}

function Wait-Condition {
    param(
        [scriptblock]$Probe,
        [int]$Seconds
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        $result = & $Probe
        if ($result.Passed) {
            return $result
        }

        Start-Sleep -Seconds 5
    }
    while ((Get-Date) -lt $deadline)

    return $result
}

function Test-HttpEndpoint {
    param(
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return [pscustomobject]@{
            Passed = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
            Detail = "HTTP $($response.StatusCode)"
        }
    }
    catch {
        return [pscustomobject]@{
            Passed = $false
            Detail = $_.Exception.Message
        }
    }
}

if ($StartServices) {
    $up = Invoke-Compose -ComposeArgs @("up", "-d", "mysql", "redis", "etcd", "minio", "milvus", "qdrant")
    Add-Result -Name "docker compose up core infra" -Passed ($up.ExitCode -eq 0) -Detail ($(if ($up.Output) { $up.Output } else { "started" }))
}

if (-not (Test-HasValues -Map $envMap -Keys @("MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"))) {
    throw ".env is missing generated MySQL/MinIO credentials. Re-run scripts/p0/Initialize-AimsEnv.ps1 -Force."
}

$mysqlPing = Wait-Condition -Seconds $TimeoutSeconds -Probe {
    $probe = Invoke-Compose -ComposeArgs @("exec", "-T", "mysql", "mysqladmin", "ping", "-h", "127.0.0.1", "-uroot", "-p$($envMap.MYSQL_ROOT_PASSWORD)", "--silent")
    [pscustomobject]@{
        Passed = ($probe.ExitCode -eq 0)
        Detail = $(if ($probe.Output) { $probe.Output } else { "mysqladmin ping succeeded" })
    }
}
Add-Result -Name "MySQL ping" -Passed $mysqlPing.Passed -Detail $mysqlPing.Detail

$mysqlSchema = Invoke-Compose -ComposeArgs @("exec", "-T", "mysql", "mysql", "--batch", "--skip-column-names", "-h", "127.0.0.1", "-uroot", "-p$($envMap.MYSQL_ROOT_PASSWORD)", "-e", "SHOW DATABASES LIKE 'aims'; USE aims; SHOW TABLES; SELECT COUNT(*) FROM cron_jobs;")
$mysqlSchemaPassed = ($mysqlSchema.ExitCode -eq 0) -and ($mysqlSchema.Output -match "(?m)^aims$") -and ($mysqlSchema.Output -match "(?m)^sessions$") -and ($mysqlSchema.Output -match "(?m)^knowledge_docs$") -and ($mysqlSchema.Output -match "(?m)^8$")
Add-Result -Name "MySQL schema and seed data" -Passed $mysqlSchemaPassed -Detail $mysqlSchema.Output

$redisPing = Wait-Condition -Seconds $TimeoutSeconds -Probe {
    $probe = Invoke-Compose -ComposeArgs @("exec", "-T", "redis", "redis-cli", "ping")
    [pscustomobject]@{
        Passed = ($probe.ExitCode -eq 0) -and ($probe.Output -match "PONG")
        Detail = $probe.Output
    }
}
Add-Result -Name "Redis ping" -Passed $redisPing.Passed -Detail $redisPing.Detail

$minioHealth = Wait-Condition -Seconds $TimeoutSeconds -Probe {
    Test-HttpEndpoint -Url ("http://127.0.0.1:{0}/minio/health/live" -f $minioApiPort)
}
Add-Result -Name "MinIO health" -Passed $minioHealth.Passed -Detail $minioHealth.Detail

$milvusHealth = Wait-Condition -Seconds $TimeoutSeconds -Probe {
    $probe = Test-HttpEndpoint -Url ("http://127.0.0.1:{0}/healthz" -f $milvusHealthPort)
    if ($probe.Passed) {
        try {
            $probe.Detail = (Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/healthz" -f $milvusHealthPort) -UseBasicParsing -TimeoutSec 5).Content
        }
        catch {
        }
    }

    $probe
}
Add-Result -Name "Milvus health" -Passed $milvusHealth.Passed -Detail $milvusHealth.Detail

$qdrantHealth = Wait-Condition -Seconds $TimeoutSeconds -Probe {
    Test-HttpEndpoint -Url ("http://127.0.0.1:{0}/readyz" -f $qdrantHttpPort)
}
Add-Result -Name "Qdrant readiness" -Passed $qdrantHealth.Passed -Detail $qdrantHealth.Detail

$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
