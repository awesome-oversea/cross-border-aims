param(
    [string]$EnvPath,
    [switch]$UseLocalLlm,
    [switch]$UseMirrorRegistry,
    [switch]$UseWsl,
    [string]$Distro,
    [switch]$AsJson,
    [int]$TimeoutSeconds = 8
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$effectiveEnvPath = if ($EnvPath) { $EnvPath } else { Join-Path $repoRoot ".env" }

if (-not (Test-Path -LiteralPath $effectiveEnvPath)) {
    throw ".env is missing. Run scripts/p0/Initialize-AimsEnv.ps1 first."
}

$envMap = Read-AimsDotEnv -Path $effectiveEnvPath
$composeFiles = Resolve-AimsComposeFiles -RepoRoot $repoRoot -UseMirrorRegistry:$UseMirrorRegistry -UseLocalLlm:$UseLocalLlm

function Expand-AimsComposeValue {
    param(
        [string]$Value
    )

    $expanded = [string]$Value
    $pattern = "\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}"
    while ($expanded -match $pattern) {
        $key = $matches[1]
        $fallback = if ($matches.Count -ge 4) { $matches[3] } else { "" }
        $replacement = Get-AimsEnvValueOrDefault -Map $envMap -Key $key -Default $fallback
        $expanded = [regex]::Replace($expanded, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{
            param($match)
            $matchKey = $match.Groups[1].Value
            if ($matchKey -eq $key) {
                return $replacement
            }
            return $match.Value
        }, 1)
    }

    return $expanded.Trim()
}

function Get-LocalDockerImageSet {
    if ($UseWsl) {
        $wslBaseArgs = @()
        if (-not [string]::IsNullOrWhiteSpace($Distro)) {
            $wslBaseArgs += @("-d", $Distro)
        }

        $output = & wsl.exe @wslBaseArgs bash -lc "docker image ls --format '{{.Repository}}:{{.Tag}}'" 2>&1
        $exitCode = $LASTEXITCODE
        $text = ($output | Out-String).Trim()
        $images = @($text -split "`r?`n" | Where-Object {
            -not [string]::IsNullOrWhiteSpace($_) -and $_ -notmatch "docker|Docker|command|recommend|http"
        } | ForEach-Object { $_.Trim() })

        return [pscustomobject]@{
            Passed = ($exitCode -eq 0)
            Detail = $(if ($exitCode -eq 0) { "ok" } elseif ([string]::IsNullOrWhiteSpace($text)) { "wsl docker image ls failed with no output" } else { $text })
            Images = $images
        }
    }

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $filePath = "docker.exe"
        $arguments = @("image", "ls", "--format", "{{.Repository}}:{{.Tag}}")

        $process = Start-Process -FilePath $filePath -ArgumentList $arguments -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        if ($null -eq $process) {
            return [pscustomobject]@{
                Passed = $false
                Detail = "failed to start " + $filePath
                Images = @()
            }
        }

        $exited = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $exited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            return [pscustomobject]@{
                Passed = $false
                Detail = ("{0} image ls timeout" -f $(if ($UseWsl) { "wsl docker" } else { "docker" }))
                Images = @()
            }
        }

        $stdout = [string]$(if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { "" })
        $stderr = [string]$(if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { "" })
        $images = @($stdout -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim() })

        $detailText = if ($process.ExitCode -eq 0) {
            "ok"
        }
        elseif ([string]::IsNullOrWhiteSpace($stderr)) {
            ("docker image ls exited {0} with no stderr" -f $process.ExitCode)
        }
        else {
            [string]$stderr
        }

        return [pscustomobject]@{
            Passed = ($process.ExitCode -eq 0)
            Detail = $detailText
            Images = $images
        }
    }
    catch {
        return [pscustomobject]@{
            Passed = $false
            Detail = $_.Exception.Message
            Images = @()
        }
    }
    finally {
        Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
}

$imageMap = [ordered]@{}
foreach ($composeFile in $composeFiles) {
    if (-not (Test-Path -LiteralPath $composeFile)) {
        continue
    }

    $lines = Get-Content -LiteralPath $composeFile
    foreach ($line in $lines) {
        if ($line -match "^\s*image:\s+(.+?)\s*$") {
            $rawImage = $matches[1].Trim().Trim('"').Trim("'")
            $image = Expand-AimsComposeValue -Value $rawImage
            if (-not [string]::IsNullOrWhiteSpace($image) -and -not $imageMap.Contains($image)) {
                $imageMap[$image] = New-Object System.Collections.Generic.List[string]
            }

            if (-not [string]::IsNullOrWhiteSpace($image)) {
                $imageMap[$image].Add((Split-Path -Leaf $composeFile))
            }
        }
    }
}

$results = New-Object System.Collections.Generic.List[object]
$localImageSet = Get-LocalDockerImageSet
foreach ($entry in $imageMap.GetEnumerator()) {
    $image = [string]$entry.Key
    $found = @($localImageSet.Images | Where-Object { $_ -eq $image }).Count -gt 0
    $results.Add([pscustomobject]@{
        Status = if ($localImageSet.Passed -and $found) { "PASS" } else { "FAIL" }
        Image  = $image
        Sources = ($entry.Value.ToArray() | Sort-Object -Unique) -join ", "
        Detail = $(if (-not $localImageSet.Passed) { [string]$localImageSet.Detail } elseif ($found) { "local" } else { "missing locally" })
    })
}

if ($AsJson) {
    [pscustomobject]@{
        envPath = $effectiveEnvPath
        mode = $(if ($UseWsl) { "wsl" } else { "windows" })
        composeFiles = @($composeFiles)
        results = @($results.ToArray())
    } | ConvertTo-Json -Depth 8
}
else {
    $results | Format-Table -AutoSize
}

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    exit 1
}

exit 0
