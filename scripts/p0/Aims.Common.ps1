Set-StrictMode -Version Latest

function Get-AimsRepoRoot {
    param(
        [string]$ScriptRoot
    )

    return (Split-Path -Parent (Split-Path -Parent $ScriptRoot))
}

function Read-AimsDotEnv {
    param(
        [string]$Path
    )

    $values = @{}

    if (-not (Test-Path -LiteralPath $Path)) {
        return $values
    }

    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        if ($line.TrimStart().StartsWith("#")) {
            continue
        }

        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) {
            continue
        }

        $values[$parts[0]] = $parts[1]
    }

    return $values
}

function Set-AimsDotEnvValues {
    param(
        [string]$Path,
        [hashtable]$Values
    )

    $existingLines = @()
    if (Test-Path -LiteralPath $Path) {
        $existingLines = @(Get-Content -LiteralPath $Path -Encoding UTF8)
    }

    $updatedKeys = @{}
    $newLines = foreach ($line in $existingLines) {
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2 -and $Values.ContainsKey($parts[0])) {
            $updatedKeys[$parts[0]] = $true
            "{0}={1}" -f $parts[0], $Values[$parts[0]]
        }
        else {
            $line
        }
    }

    foreach ($key in $Values.Keys) {
        if (-not $updatedKeys.ContainsKey($key)) {
            $newLines += ("{0}={1}" -f $key, $Values[$key])
        }
    }

    Set-Content -LiteralPath $Path -Value $newLines -Encoding UTF8
}

function New-AimsHexSecret {
    param(
        [int]$ByteCount = 32
    )

    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $bytes = New-Object byte[] $ByteCount
        $rng.GetBytes($bytes)
        return [System.BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $rng.Dispose()
    }
}

function New-AimsAlphaNumericSecret {
    param(
        [int]$Length = 24
    )

    $alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()

    try {
        $chars = New-Object char[] $Length
        $buffer = New-Object byte[] $Length
        $rng.GetBytes($buffer)

        for ($i = 0; $i -lt $Length; $i++) {
            $chars[$i] = $alphabet[$buffer[$i] % $alphabet.Length]
        }

        return -join $chars
    }
    finally {
        $rng.Dispose()
    }
}

function Get-AimsLocalLlmComposePath {
    param(
        [string]$RepoRoot
    )

    return (Join-Path $RepoRoot "docker-compose.local-llm.yml")
}

function Resolve-AimsComposeFiles {
    param(
        [string]$RepoRoot,
        [switch]$UseMirrorRegistry,
        [switch]$UseLocalLlm
    )

    $composeFiles = New-Object System.Collections.Generic.List[string]
    $primaryComposePath = Join-Path $RepoRoot "docker-compose.yml"
    $composeFiles.Add($primaryComposePath)

    if ($UseMirrorRegistry) {
        $mirrorComposePath = Join-Path $RepoRoot "docker-compose.mirror.yml"
        if (-not (Test-Path -LiteralPath $mirrorComposePath)) {
            throw "Mirror compose file not found: $mirrorComposePath"
        }

        $composeFiles.Add($mirrorComposePath)
    }

    if ($UseLocalLlm) {
        $localLlmComposePath = Get-AimsLocalLlmComposePath -RepoRoot $RepoRoot
        if (-not (Test-Path -LiteralPath $localLlmComposePath)) {
            throw "Local LLM compose file not found: $localLlmComposePath"
        }

        $composeFiles.Add($localLlmComposePath)
    }

    return ,($composeFiles.ToArray())
}

function New-AimsComposeCommandArguments {
    param(
        [string[]]$ComposeFiles,
        [string[]]$AdditionalArgs
    )

    $arguments = New-Object System.Collections.Generic.List[string]
    $arguments.Add("compose")

    foreach ($composeFile in $ComposeFiles) {
        $arguments.Add("-f")
        $arguments.Add($composeFile)
    }

    foreach ($argument in $AdditionalArgs) {
        $arguments.Add($argument)
    }

    return $arguments.ToArray()
}

function Get-AimsEnvValueOrDefault {
    param(
        [hashtable]$Map,
        [string]$Key,
        [string]$Default
    )

    if ($null -ne $Map -and $Map.ContainsKey($Key) -and -not [string]::IsNullOrWhiteSpace($Map[$Key])) {
        return [string]$Map[$Key]
    }

    return $Default
}
