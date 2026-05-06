param(
    [string]$ManifestPath,
    [string]$ProfilePath,
    [string]$OutputDir,
    [switch]$RefreshManifest,
    [int]$DefaultMinChars = 500,
    [int]$DefaultMaxChars = 900,
    [int]$DefaultOverlapChars = 120
)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "p0\Aims.Common.ps1")

$repoRoot = Get-AimsRepoRoot -ScriptRoot $PSScriptRoot
$outputRoot = if ($OutputDir) { $OutputDir } else { Join-Path $repoRoot "data\knowledge" }
$manifestFile = if ($ManifestPath) { $ManifestPath } else { Join-Path $outputRoot "knowledge-manifest.json" }
$profileFile = if ($ProfilePath) { $ProfilePath } else { Join-Path $repoRoot "fixtures\knowledge\import-profiles.json" }

if ($RefreshManifest -or -not (Test-Path -LiteralPath $manifestFile)) {
    & (Join-Path $PSScriptRoot "Export-AimsKnowledgeManifest.ps1") -OutputDir $outputRoot
    if (-not $?) {
        throw "Failed to refresh knowledge manifest."
    }
}

if (-not (Test-Path -LiteralPath $manifestFile)) {
    throw "Knowledge manifest not found: $manifestFile"
}

if (-not (Test-Path -LiteralPath $profileFile)) {
    throw "Knowledge import profile file not found: $profileFile"
}

$manifestData = Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8 | ConvertFrom-Json
$manifest = if ($manifestData -is [System.Array]) { $manifestData } else { @($manifestData) }
$profileData = Get-Content -LiteralPath $profileFile -Raw -Encoding UTF8 | ConvertFrom-Json
$profiles = if ($profileData.profiles -is [System.Array]) { $profileData.profiles } else { @($profileData.profiles) }
$profileMap = @{}
foreach ($profile in $profiles) {
    $profileMap[$profile.importBatch] = $profile
}

function Get-ImportProfile {
    param(
        [string]$ImportBatch
    )

    if ($profileMap.ContainsKey($ImportBatch)) {
        return $profileMap[$ImportBatch]
    }

    return [pscustomobject]@{
        importBatch = $ImportBatch
        engine = "milvus"
        collection = "aims_misc"
        chunking = [pscustomobject]@{
            minChars = $DefaultMinChars
            maxChars = $DefaultMaxChars
            overlapChars = $DefaultOverlapChars
        }
        description = "Fallback import profile"
    }
}

function Split-AimsText {
    param(
        [string]$Text,
        [int]$MinChars,
        [int]$MaxChars,
        [int]$OverlapChars
    )

    $normalized = $Text -replace "`r`n", "`n"
    $normalized = [regex]::Replace($normalized, "[ \t]+\n", "`n")
    $normalized = [regex]::Replace($normalized, "\n{3,}", "`n`n").Trim()

    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return @()
    }

    $chunks = New-Object System.Collections.Generic.List[object]
    $start = 0

    while ($start -lt $normalized.Length) {
        $remaining = $normalized.Length - $start
        if ($remaining -le $MaxChars) {
            $end = $normalized.Length
        }
        else {
            $window = $normalized.Substring($start, $MaxChars)
            $relativeEnd = -1
            $delimiters = @("`n`n", "`n", ([string][char]0x3002), ([string][char]0xFF01), ([string][char]0xFF1F), ". ", "; ", " ")

            foreach ($delimiter in $delimiters) {
                $candidate = $window.LastIndexOf($delimiter)
                if ($candidate -ge $MinChars) {
                    $relativeEnd = $candidate + $delimiter.Length
                    break
                }
            }

            if ($relativeEnd -lt 0) {
                $relativeEnd = $MaxChars
            }

            $end = $start + $relativeEnd
        }

        if ($end -le $start) {
            $end = [Math]::Min($normalized.Length, $start + $MaxChars)
        }

        $chunkText = $normalized.Substring($start, $end - $start).Trim()
        if (-not [string]::IsNullOrWhiteSpace($chunkText)) {
            $chunks.Add([pscustomobject]@{
                startChar = $start
                endChar   = $end
                charCount = $chunkText.Length
                text      = $chunkText
            })
        }

        if ($end -ge $normalized.Length) {
            break
        }

        $nextStart = [Math]::Max($start + 1, $end - $OverlapChars)
        if ($nextStart -le $start) {
            $nextStart = $end
        }

        $start = $nextStart
    }

    return $chunks.ToArray()
}

if (-not (Test-Path -LiteralPath $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
}

$chunkPath = Join-Path $outputRoot "knowledge-chunks.jsonl"
$summaryPath = Join-Path $outputRoot "knowledge-chunk-summary.json"
$planPath = Join-Path $outputRoot "knowledge-import-plan.json"

$chunkLines = New-Object System.Collections.Generic.List[string]
$chunkRecords = New-Object System.Collections.Generic.List[object]
$warnings = New-Object System.Collections.Generic.List[string]

foreach ($entry in $manifest) {
    $sourcePath = Join-Path $repoRoot ([string]$entry.sourcePath)
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        $warnings.Add("Missing source file: $sourcePath")
        continue
    }

    $profile = Get-ImportProfile -ImportBatch $entry.importBatch
    $content = Get-Content -LiteralPath $sourcePath -Raw -Encoding UTF8
    $chunks = Split-AimsText -Text $content -MinChars $profile.chunking.minChars -MaxChars $profile.chunking.maxChars -OverlapChars $profile.chunking.overlapChars

    for ($index = 0; $index -lt $chunks.Count; $index++) {
        $chunk = $chunks[$index]
        $record = [pscustomobject]@{
            id             = ("{0}-{1:D4}" -f $entry.id, ($index + 1))
            docId          = $entry.id
            title          = $entry.title
            sourcePath     = $entry.sourcePath
            sourceGroup    = $entry.sourceGroup
            importBatch    = $entry.importBatch
            categoryKey    = $entry.categoryKey
            categoryName   = $entry.categoryName
            priority       = $entry.priority
            tags           = @($entry.tags)
            engineHint     = $profile.engine
            collectionHint = $profile.collection
            chunkIndex     = $index + 1
            chunkCount     = $chunks.Count
            startChar      = $chunk.startChar
            endChar        = $chunk.endChar
            charCount      = $chunk.charCount
            text           = $chunk.text
        }

        $chunkRecords.Add($record)
        $chunkLines.Add(($record | ConvertTo-Json -Compress -Depth 10))
    }
}

$chunkLines | Set-Content -LiteralPath $chunkPath -Encoding UTF8

$summary = [pscustomobject]@{
    generatedAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    manifestPath = $manifestFile.Replace($repoRoot + "\", "")
    profilePath = $profileFile.Replace($repoRoot + "\", "")
    totalDocs = $manifest.Count
    processedDocs = (@($chunkRecords | Select-Object -ExpandProperty docId -Unique)).Count
    totalChunks = $chunkRecords.Count
    warnings = @($warnings)
    byBatch = ($chunkRecords | Group-Object importBatch | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{
            importBatch = $_.Name
            chunkCount = $_.Count
            docCount = (@($_.Group | Select-Object -ExpandProperty docId -Unique)).Count
        }
    })
    byCollection = ($chunkRecords | Group-Object collectionHint | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{
            collection = $_.Name
            engine = $_.Group[0].engineHint
            chunkCount = $_.Count
            docCount = (@($_.Group | Select-Object -ExpandProperty docId -Unique)).Count
        }
    })
}

$summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

$plan = ($chunkRecords | Group-Object { "{0}|{1}|{2}" -f $_.importBatch, $_.engineHint, $_.collectionHint } | Sort-Object Name | ForEach-Object {
    $first = $_.Group[0]
    [pscustomobject]@{
        importBatch = $first.importBatch
        engine = $first.engineHint
        collection = $first.collectionHint
        docCount = (@($_.Group | Select-Object -ExpandProperty docId -Unique)).Count
        chunkCount = $_.Count
        suggestedTopK = 5
    }
})

$plan | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $planPath -Encoding UTF8

Write-Host "Knowledge chunks written to $chunkPath"
Write-Host "Knowledge chunk summary written to $summaryPath"
Write-Host "Knowledge import plan written to $planPath"
Write-Host ("Documents processed: " + $summary.processedDocs + "/" + $summary.totalDocs)
Write-Host ("Chunks generated: " + $summary.totalChunks)

if ($warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "Warnings:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host ("- " + $warning) -ForegroundColor Yellow
    }
}

if ($chunkRecords.Count -eq 0) {
    exit 1
}

exit 0
