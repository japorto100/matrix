# backup-before-v1.6.ps1 -- Pre-flight DB + Media backup before starting Tuwunel v1.6.0-rc
#
# Why: v1.6.0-rc performs irreversible schema migrations. If the RC breaks something,
# restoring from this backup is the only way back to v1.5.1.
#
# Usage: .\scripts\backup-before-v1.6.ps1
#
# Requirement: Tuwunel must NOT be running. RocksDB holds a file lock while alive;
# copying a live DB yields an inconsistent snapshot.

$ErrorActionPreference = "Stop"
$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$dataDir  = Join-Path $repoRoot "homeserver\data"
$dbSrc    = Join-Path $dataDir "db"
$dbDst    = Join-Path $dataDir "db-pre-v1.6"
$mediaSrc = Join-Path $dataDir "media"
$mediaDst = Join-Path $dataDir "media-pre-v1.6"

Write-Host "== Tuwunel v1.6.0-rc pre-flight backup ==" -ForegroundColor Cyan

# Sanity: is tuwunel listening on 8448?
$listening = Get-NetTCPConnection -State Listen -LocalPort 8448 -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host "ERROR: Something is listening on port 8448 (likely Tuwunel)." -ForegroundColor Red
    Write-Host "       Stop the devstack first: Ctrl+C in the devstack window, or close the PowerShell window." -ForegroundColor Red
    Write-Host "       Then re-run this script." -ForegroundColor Red
    exit 1
}

# Check DB source exists
if (-not (Test-Path $dbSrc)) {
    Write-Host "WARN: $dbSrc does not exist -- nothing to back up (fresh install?)." -ForegroundColor Yellow
    Write-Host "      Continuing anyway -- the v1.6 start will create a fresh DB." -ForegroundColor Yellow
    exit 0
}

# Refuse to overwrite existing backup
if (Test-Path $dbDst) {
    Write-Host "ERROR: Backup already exists at $dbDst" -ForegroundColor Red
    Write-Host "       If you are sure you want to overwrite, delete it manually first:" -ForegroundColor Red
    Write-Host "         Remove-Item -Recurse -Force '$dbDst'" -ForegroundColor DarkGray
    if (Test-Path $mediaDst) {
        Write-Host "         Remove-Item -Recurse -Force '$mediaDst'" -ForegroundColor DarkGray
    }
    exit 1
}

# DB backup
$dbSize = (Get-ChildItem $dbSrc -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Host "[1/2] Copying DB ($([math]::Round($dbSize/1MB,1)) MB)..." -ForegroundColor Green
Write-Host "      $dbSrc" -ForegroundColor DarkGray
Write-Host "      -> $dbDst" -ForegroundColor DarkGray
Copy-Item -Path $dbSrc -Destination $dbDst -Recurse -Force

# Media backup
if (Test-Path $mediaSrc) {
    $mediaSize = (Get-ChildItem $mediaSrc -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    Write-Host "[2/2] Copying Media ($([math]::Round($mediaSize/1MB,1)) MB)..." -ForegroundColor Green
    Write-Host "      $mediaSrc" -ForegroundColor DarkGray
    Write-Host "      -> $mediaDst" -ForegroundColor DarkGray
    Copy-Item -Path $mediaSrc -Destination $mediaDst -Recurse -Force
} else {
    Write-Host "[2/2] Media directory $mediaSrc does not exist -- skipping" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "== Backup complete ==" -ForegroundColor Cyan
Write-Host "Rollback procedure (if v1.6-rc breaks things):" -ForegroundColor DarkCyan
Write-Host "  1. Stop devstack (close the PowerShell window or Ctrl+C)" -ForegroundColor DarkGray
Write-Host "  2. Remove-Item -Recurse -Force '$dbSrc'" -ForegroundColor DarkGray
Write-Host "  3. Copy-Item -Recurse '$dbDst' '$dbSrc'" -ForegroundColor DarkGray
if (Test-Path $mediaDst) {
    Write-Host "  4. Remove-Item -Recurse -Force '$mediaSrc'" -ForegroundColor DarkGray
    Write-Host "  5. Copy-Item -Recurse '$mediaDst' '$mediaSrc'" -ForegroundColor DarkGray
}
Write-Host "  6. .\scripts\dev-stack2.ps1   (without -Tuwunel16)" -ForegroundColor DarkGray
