# PowerShell-native equivalent of download_datasets.py (Windows 11, PowerShell 5.1+).
# Reads data/manifests/dataset_sources.json, downloads with curl.exe (resumable),
# verifies published checksums, computes SHA-256, writes DATASET_MANIFEST.json/.csv.
# Entries marked "blocked" (e.g. LANL e-mail form) are recorded, never bypassed.
param(
    [string[]]$Only = @(),
    [switch]$SkipLarge
)
$ErrorActionPreference = "Stop"
$DataDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RawDir = Join-Path $DataDir "raw"
$Registry = Get-Content (Join-Path $DataDir "manifests\dataset_sources.json") -Raw | ConvertFrom-Json
$Entries = @()

foreach ($src in $Registry.sources) {
    if ($Only.Count -gt 0 -and -not ($Only -contains $src.id)) { continue }
    $entry = [ordered]@{
        id = $src.id; dataset = $src.dataset; version = $src.version; organization = $src.organization
        source_page = $src.source_page; url = $src.url; doi = $src.doi; license = $src.license
        published_checksum = $src.published_checksum; role = $src.role
        retrieval_date = (Get-Date).ToUniversalTime().ToString("s") + "Z"
        status = $null; local_path = $null; size_bytes = $null; sha256 = $null; md5 = $null
        checksum_verified = $null; blocker = $null
    }
    if ($src.blocked) {
        $entry.status = "blocked"; $entry.blocker = $src.blocked
        Write-Host "[BLOCKED] $($src.id)"
        $Entries += [pscustomobject]$entry; continue
    }
    $dest = Join-Path $RawDir ($src.filename -replace "/", "\")
    New-Item -ItemType Directory -Force (Split-Path -Parent $dest) | Out-Null
    try {
        if (-not (Test-Path $dest)) {
            if ($SkipLarge) {
                $len = [int64]((curl.exe -sIL $src.url | Select-String -Pattern "^content-length:\s*(\d+)" | Select-Object -Last 1).Matches.Groups[1].Value)
                if ($len -gt 1GB) { $entry.status = "skipped_large"; $Entries += [pscustomobject]$entry; continue }
            }
            Write-Host "[DOWNLOAD] $($src.id)"
            $part = "$dest.part"
            for ($i = 0; $i -lt 8; $i++) {
                curl.exe -L --fail --retry 5 -C - -o $part $src.url
                if ($LASTEXITCODE -eq 0) { break }
                Start-Sleep -Seconds (5 * ($i + 1))
            }
            if ($LASTEXITCODE -ne 0) { throw "curl failed with exit code $LASTEXITCODE" }
            Move-Item -Force $part $dest
        }
        $entry.local_path = "data/raw/" + $src.filename
        $entry.size_bytes = (Get-Item $dest).Length
        $entry.sha256 = (Get-FileHash -Algorithm SHA256 $dest).Hash.ToLower()
        $entry.md5 = (Get-FileHash -Algorithm MD5 $dest).Hash.ToLower()
        if ($src.published_checksum) {
            $parts = $src.published_checksum.Split(":", 2)
            $entry.checksum_verified = ($entry[$parts[0]] -eq $parts[1].ToLower())
        }
        $entry.status = "downloaded"
        Write-Host "    $($entry.size_bytes) bytes sha256=$($entry.sha256) verified=$($entry.checksum_verified)"
    } catch {
        $entry.status = "failed"; $entry.blocker = $_.Exception.Message
        Write-Warning "[FAILED] $($src.id): $($_.Exception.Message)"
    }
    $Entries += [pscustomobject]$entry
}

$manifest = [ordered]@{ generated_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"; selection_rationale = $Registry.selection_rationale; entries = $Entries }
$manifest | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 (Join-Path $DataDir "DATASET_MANIFEST.json")
$Entries | Select-Object id, dataset, version, organization, source_page, url, doi, license, retrieval_date, status, local_path, size_bytes, sha256, md5, published_checksum, checksum_verified, blocker |
    Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $DataDir "DATASET_MANIFEST.csv")
