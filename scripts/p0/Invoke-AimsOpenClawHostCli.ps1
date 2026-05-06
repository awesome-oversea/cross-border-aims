[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$PortableRoot = "D:\openclaw\openclaw-portable-win-x64",
    [string]$EnvPath,
    [string]$HomeRoot,
    [switch]$SkipSyncHome,
    [switch]$RunGateway,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$OpenClawArgs
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$envPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }
$homeRoot = if ($HomeRoot) { $HomeRoot } else { Join-Path $repoRoot ".generated\openclaw-host-home" }

$resolvedPortableRoot = [System.IO.Path]::GetFullPath($PortableRoot)
$resolvedEnvPath = [System.IO.Path]::GetFullPath($envPath)
$resolvedHomeRoot = [System.IO.Path]::GetFullPath($homeRoot)

$PortableRoot = $resolvedPortableRoot
$envPath = $resolvedEnvPath
$homeRoot = $resolvedHomeRoot
$cliPath = Join-Path $PortableRoot "openclaw.mjs"
$runtimeTmpRoot = Join-Path $repoRoot "runtime\tmp"

if (-not (Test-Path -LiteralPath $cliPath)) {
    throw "OpenClaw portable entry not found: $cliPath"
}

function Ensure-PortableTemplateFile {
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

function ConvertTo-WindowsCommandLineArgument {
    param([string]$Value)

    if ($null -eq $Value) {
        return '""'
    }

    if ($Value.Length -eq 0) {
        return '""'
    }

    if ($Value -notmatch '[\s"]') {
        return $Value
    }

    $builder = New-Object System.Text.StringBuilder
    $null = $builder.Append('"')
    $pendingBackslashes = 0

    foreach ($char in $Value.ToCharArray()) {
        if ($char -eq '\') {
            $pendingBackslashes += 1
            continue
        }

        if ($char -eq '"') {
            $null = $builder.Append((New-Object string([char]92, (($pendingBackslashes * 2) + 1))))
            $pendingBackslashes = 0
            $null = $builder.Append('"')
            continue
        }

        if ($pendingBackslashes -gt 0) {
            $null = $builder.Append((New-Object string([char]92, $pendingBackslashes)))
            $pendingBackslashes = 0
        }

        $null = $builder.Append($char)
    }

    if ($pendingBackslashes -gt 0) {
        $null = $builder.Append((New-Object string([char]92, ($pendingBackslashes * 2))))
    }

    $null = $builder.Append('"')
    return $builder.ToString()
}

$portableTemplateRoot = Join-Path $PortableRoot "docs\reference\templates"
Ensure-PortableTemplateFile -DestinationPath (Join-Path $portableTemplateRoot "AGENTS.md") -SourcePath (Join-Path $repoRoot "AGENTS.md") -FallbackContent "# OpenClaw Workspace`r`n"
Ensure-PortableTemplateFile -DestinationPath (Join-Path $portableTemplateRoot "SOUL.md") -SourcePath (Join-Path $repoRoot "SOUL.md") -FallbackContent "# OpenClaw Soul`r`n"
Ensure-PortableTemplateFile -DestinationPath (Join-Path $portableTemplateRoot "TOOLS.md") -SourcePath (Join-Path $repoRoot "TOOLS.md") -FallbackContent "# Workspace Tools`r`n`r`n- Record local tooling notes here.`r`n"
Ensure-PortableTemplateFile -DestinationPath (Join-Path $portableTemplateRoot "IDENTITY.md") -SourcePath "" -FallbackContent "# Identity`r`n`r`n- Name: AIMS`r`n- Theme: AI marketing system`r`n- Emoji: crab`r`n"
Ensure-PortableTemplateFile -DestinationPath (Join-Path $portableTemplateRoot "USER.md") -SourcePath "" -FallbackContent "# User`r`n`r`n- Add local operator notes here.`r`n"
Ensure-PortableTemplateFile -DestinationPath (Join-Path $portableTemplateRoot "BOOT.md") -SourcePath "" -FallbackContent "# Boot`r`n`r`n- Review workspace guidance before replying.`r`n"
Ensure-PortableTemplateFile -DestinationPath (Join-Path $portableTemplateRoot "BOOTSTRAP.md") -SourcePath "" -FallbackContent "# Bootstrap`r`n`r`n- Initialize the workspace from available project guidance.`r`n"
Ensure-PortableTemplateFile -DestinationPath (Join-Path $portableTemplateRoot "HEARTBEAT.md") -SourcePath "" -FallbackContent "# Heartbeat`r`n`r`n- Keep background follow-ups concise and actionable.`r`n"

if (-not $SkipSyncHome) {
    & (Join-Path $PSScriptRoot "Sync-AimsOpenClawHostHome.ps1") -EnvPath $envPath -HomeRoot $homeRoot | Out-Null
    if (-not $?) {
        throw "Failed to sync host OpenClaw home."
    }
}

if ($null -eq $OpenClawArgs) {
    $OpenClawArgs = @()
}

if ($RunGateway -and $OpenClawArgs.Count -eq 0) {
    $OpenClawArgs = @("gateway", "run")
}

$envMap = Read-AimsDotEnv -Path $envPath
foreach ($entry in $envMap.GetEnumerator()) {
    if (-not [string]::IsNullOrWhiteSpace([string]$entry.Value)) {
        [System.Environment]::SetEnvironmentVariable($entry.Key, [string]$entry.Value, "Process")
    }
}

if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable("OPENCLAW_GATEWAY_TOKEN", "Process"))) {
    $gatewayToken = [System.Environment]::GetEnvironmentVariable("AIMS_GATEWAY_TOKEN", "Process")
    if (-not [string]::IsNullOrWhiteSpace($gatewayToken)) {
        [System.Environment]::SetEnvironmentVariable("OPENCLAW_GATEWAY_TOKEN", $gatewayToken, "Process")
    }
}

if (-not (Test-Path -LiteralPath $runtimeTmpRoot)) {
    New-Item -ItemType Directory -Path $runtimeTmpRoot -Force | Out-Null
}

[System.Environment]::SetEnvironmentVariable("HOME", $homeRoot, "Process")
[System.Environment]::SetEnvironmentVariable("USERPROFILE", $homeRoot, "Process")
[System.Environment]::SetEnvironmentVariable("HOMEDRIVE", ([System.IO.Path]::GetPathRoot($homeRoot)).TrimEnd("\"), "Process")
[System.Environment]::SetEnvironmentVariable("HOMEPATH", $homeRoot.Substring(2), "Process")
[System.Environment]::SetEnvironmentVariable("TMP", $runtimeTmpRoot, "Process")
[System.Environment]::SetEnvironmentVariable("TEMP", $runtimeTmpRoot, "Process")
[System.Environment]::SetEnvironmentVariable("TMPDIR", $runtimeTmpRoot, "Process")
[System.Environment]::SetEnvironmentVariable("OPENCLAW_SERVICE_MARKER", "aims-host-gateway", "Process")

Push-Location $PortableRoot
try {
    $isLongRunningGateway = $false
    if ($OpenClawArgs.Count -ge 1 -and $OpenClawArgs[0] -eq "gateway") {
        $isLongRunningGateway = ($OpenClawArgs.Count -eq 1)
        if (-not $isLongRunningGateway -and $OpenClawArgs[1] -eq "run") {
            $isLongRunningGateway = $true
        }
        if (-not $isLongRunningGateway -and $OpenClawArgs[1].StartsWith("-")) {
            $isLongRunningGateway = $true
        }
    }
    if ($isLongRunningGateway) {
        & node $cliPath @OpenClawArgs
        exit $LASTEXITCODE
    }

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()
    $argumentLine = ((@($cliPath) + $OpenClawArgs) | ForEach-Object { ConvertTo-WindowsCommandLineArgument -Value ([string]$_) }) -join " "

    try {
        $process = Start-Process -FilePath "node.exe" -ArgumentList $argumentLine -WorkingDirectory $PortableRoot -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue } else { "" }
        $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue } else { "" }

        if (-not [string]::IsNullOrWhiteSpace($stdout)) {
            Write-Output ($stdout.TrimEnd())
        }

        if (-not [string]::IsNullOrWhiteSpace($stderr)) {
            Write-Output ($stderr.TrimEnd())
        }

        exit $process.ExitCode
    }
    finally {
        Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
}
finally {
    Pop-Location
}
