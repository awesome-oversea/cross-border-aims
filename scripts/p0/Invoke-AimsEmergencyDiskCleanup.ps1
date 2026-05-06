param(
    [switch]$IncludeUpdaterCache,
    [switch]$IncludeBrowserCaches
)

$ErrorActionPreference = "Stop"

$results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param(
        [string]$Name,
        [int64]$BytesRemoved,
        [int]$ItemsRemoved,
        [string]$Detail
    )

    $results.Add([pscustomobject]@{
        Name         = $Name
        ItemsRemoved = $ItemsRemoved
        FreedMB      = [math]::Round($BytesRemoved / 1MB, 2)
        Detail       = $Detail
    })
}

function Get-DriveFreeBytes {
    param(
        [string]$DriveName
    )

    $drive = Get-PSDrive -Name $DriveName -ErrorAction Stop
    return [int64]$drive.Free
}

function Get-FileBytes {
    param(
        [string[]]$Paths
    )

    $total = 0L
    foreach ($path in $Paths) {
        $exists = $false
        try {
            $exists = Test-Path -LiteralPath $path
        }
        catch {
            $exists = $false
        }

        if (-not $exists) {
            continue
        }

        $item = Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        if ($null -eq $item) {
            continue
        }

        if ($item.PSIsContainer) {
            foreach ($child in Get-ChildItem -LiteralPath $path -Recurse -Force -File -ErrorAction SilentlyContinue) {
                $total += [int64]$child.Length
            }
        }
        else {
            $total += [int64]$item.Length
        }
    }

    return $total
}

function Remove-PathContents {
    param(
        [string]$RootPath,
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $RootPath)) {
        Add-Result -Name $Name -BytesRemoved 0 -ItemsRemoved 0 -Detail "path missing"
        return
    }

    $items = @(Get-ChildItem -LiteralPath $RootPath -Force -ErrorAction SilentlyContinue)
    if ($items.Count -eq 0) {
        Add-Result -Name $Name -BytesRemoved 0 -ItemsRemoved 0 -Detail "nothing to remove"
        return
    }

    $paths = @($items | ForEach-Object { $_.FullName })
    $bytesBefore = Get-FileBytes -Paths $paths
    $removed = 0

    foreach ($item in $items) {
        try {
            Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction Stop
            $removed += 1
        }
        catch {
        }
    }

    $bytesAfter = Get-FileBytes -Paths $paths
    $freedBytes = [math]::Max(0, $bytesBefore - $bytesAfter)
    Add-Result -Name $Name -BytesRemoved $freedBytes -ItemsRemoved $removed -Detail $RootPath
}

function Remove-ExactPaths {
    param(
        [string[]]$Paths,
        [string]$Name
    )

    $existing = @(
        $Paths | Where-Object {
            try {
                Test-Path -LiteralPath $_
            }
            catch {
                $false
            }
        }
    )
    if ($existing.Count -eq 0) {
        Add-Result -Name $Name -BytesRemoved 0 -ItemsRemoved 0 -Detail "nothing to remove"
        return
    }

    $bytesBefore = Get-FileBytes -Paths $existing
    $removed = 0

    foreach ($path in $existing) {
        try {
            Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction Stop
            $removed += 1
        }
        catch {
        }
    }

    $bytesAfter = Get-FileBytes -Paths $existing
    $freedBytes = [math]::Max(0, $bytesBefore - $bytesAfter)
    Add-Result -Name $Name -BytesRemoved $freedBytes -ItemsRemoved $removed -Detail ($existing -join "; ")
}

$localAppData = $env:LOCALAPPDATA
$driveName = ([System.IO.Path]::GetPathRoot($localAppData)).TrimEnd("\", ":")
$freeBefore = Get-DriveFreeBytes -DriveName $driveName

Remove-PathContents -RootPath (Join-Path $localAppData "Temp") -Name "Local temp contents"
Remove-PathContents -RootPath (Join-Path $localAppData "CrashDumps") -Name "Crash dumps"
Remove-PathContents -RootPath (Join-Path $localAppData "Docker\log\host") -Name "Docker host logs"
Remove-PathContents -RootPath (Join-Path $localAppData "Docker\log\vm") -Name "Docker VM logs"

if ($IncludeUpdaterCache) {
    Remove-PathContents -RootPath (Join-Path $localAppData "open-cowork-updater\pending") -Name "OpenCoWork updater pending cache"
    Remove-ExactPaths -Paths @(
        (Join-Path $localAppData "open-cowork-updater\installer.exe"),
        (Join-Path $localAppData "open-cowork-updater\current.blockmap")
    ) -Name "OpenCoWork updater root cache"
}

if ($IncludeBrowserCaches) {
    Remove-PathContents -RootPath (Join-Path $localAppData "ms-playwright") -Name "Playwright browser cache"
    Remove-PathContents -RootPath (Join-Path $env:USERPROFILE ".agent-browser\browsers") -Name "Agent browser cache"
    Remove-PathContents -RootPath (Join-Path $localAppData "Microsoft\Edge\User Data\ProvenanceData") -Name "Edge provenance cache"
}

$freeAfter = Get-DriveFreeBytes -DriveName $driveName
$freedDriveBytes = [math]::Max(0, $freeAfter - $freeBefore)

$results | Format-Table -AutoSize
Write-Host ""
Write-Host ("Drive {0}: free before {1} MB, free after {2} MB, delta {3} MB" -f $driveName, [math]::Round($freeBefore / 1MB, 2), [math]::Round($freeAfter / 1MB, 2), [math]::Round($freedDriveBytes / 1MB, 2))
