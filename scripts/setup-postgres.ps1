# setup-postgres.ps1 — PostgreSQL 17 + pgvector Setup fuer tools/pgsql/
# Einmalig ausfuehren: .\scripts\setup-postgres.ps1
# Danach startet devstack2 automatisch.
#
# Downloads:
#   PostgreSQL 17 ZIP (Windows x64): https://www.postgresql.org/download/windows/
#   pgvector DLL: https://github.com/andreiramani/pgvector_pgsql_windows/releases

param(
    [string]$PgVersion = "17.4-1",
    [string]$PgVectorVersion = "0.8.2_17.6"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pgDir = Join-Path $repoRoot "tools\pgsql"
$pgDataDir = Join-Path $repoRoot "tools\pgsql-data"

if (Test-Path (Join-Path $pgDir "bin\pg_ctl.exe")) {
    Write-Host "PostgreSQL already installed at $pgDir" -ForegroundColor Yellow
    Write-Host "Delete tools\pgsql\ to reinstall." -ForegroundColor DarkGray
    exit 0
}

Write-Host "=== PostgreSQL + pgvector Setup ===" -ForegroundColor Cyan

# 1. Download PostgreSQL ZIP
$pgZipUrl = "https://get.enterprisedb.com/postgresql/postgresql-$PgVersion-windows-x64-binaries.zip"
$pgZipFile = Join-Path $env:TEMP "postgresql-$PgVersion-windows-x64.zip"

if (-not (Test-Path $pgZipFile)) {
    Write-Host "Downloading PostgreSQL $PgVersion..." -ForegroundColor Green
    Invoke-WebRequest -Uri $pgZipUrl -OutFile $pgZipFile -UseBasicParsing
} else {
    Write-Host "PostgreSQL ZIP already downloaded." -ForegroundColor DarkGray
}

# 2. Extract
Write-Host "Extracting to tools\pgsql\..." -ForegroundColor Green
Expand-Archive -Path $pgZipFile -DestinationPath (Join-Path $repoRoot "tools") -Force
# ZIP enthält pgsql/ Ordner direkt

if (-not (Test-Path (Join-Path $pgDir "bin\pg_ctl.exe"))) {
    Write-Host "ERROR: pg_ctl.exe not found after extraction!" -ForegroundColor Red
    exit 1
}

# 3. Download pgvector DLL
$pvZipUrl = "https://github.com/andreiramani/pgvector_pgsql_windows/releases/download/$PgVectorVersion/pgvector_pgsql17_win_x64.zip"
$pvZipFile = Join-Path $env:TEMP "pgvector-$PgVectorVersion.zip"

if (-not (Test-Path $pvZipFile)) {
    Write-Host "Downloading pgvector $PgVectorVersion..." -ForegroundColor Green
    Invoke-WebRequest -Uri $pvZipUrl -OutFile $pvZipFile -UseBasicParsing
} else {
    Write-Host "pgvector ZIP already downloaded." -ForegroundColor DarkGray
}

# 4. Extract pgvector into PostgreSQL
Write-Host "Installing pgvector extension..." -ForegroundColor Green
$pvTempDir = Join-Path $env:TEMP "pgvector_extract"
if (Test-Path $pvTempDir) { Remove-Item -Recurse -Force $pvTempDir }
Expand-Archive -Path $pvZipFile -DestinationPath $pvTempDir -Force

# Copy DLL + control + SQL files into PostgreSQL dirs
$pgShareExt = Join-Path $pgDir "share\extension"
$pgLib = Join-Path $pgDir "lib"

Get-ChildItem -Path $pvTempDir -Recurse -Filter "vector.dll" | ForEach-Object {
    Copy-Item $_.FullName -Destination $pgLib -Force
    Write-Host "  Copied vector.dll → lib\" -ForegroundColor DarkGreen
}
Get-ChildItem -Path $pvTempDir -Recurse -Filter "vector.control" | ForEach-Object {
    Copy-Item $_.FullName -Destination $pgShareExt -Force
    Write-Host "  Copied vector.control → share\extension\" -ForegroundColor DarkGreen
}
Get-ChildItem -Path $pvTempDir -Recurse -Filter "vector--*.sql" | ForEach-Object {
    Copy-Item $_.FullName -Destination $pgShareExt -Force
    Write-Host "  Copied $($_.Name) → share\extension\" -ForegroundColor DarkGreen
}

Remove-Item -Recurse -Force $pvTempDir

# 5. Init database cluster
if (-not (Test-Path $pgDataDir)) {
    Write-Host "Initializing database cluster..." -ForegroundColor Green
    $initdb = Join-Path $pgDir "bin\initdb.exe"
    & $initdb -D $pgDataDir -U postgres -E UTF8 --locale=C
}

# 6. Create hindsight_dev database
Write-Host "Starting PostgreSQL temporarily to create database..." -ForegroundColor Green
$pgCtl = Join-Path $pgDir "bin\pg_ctl.exe"
& $pgCtl start -D $pgDataDir -l (Join-Path $repoRoot "logs\postgres-setup.log") -w

Start-Sleep -Seconds 3

$psql = Join-Path $pgDir "bin\psql.exe"
$dbExists = & $psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='hindsight_dev'" 2>$null
if ($dbExists -ne "1") {
    & $psql -U postgres -c "CREATE DATABASE hindsight_dev"
    Write-Host "  Created database: hindsight_dev" -ForegroundColor DarkGreen
}
& $psql -U postgres -d hindsight_dev -c "CREATE EXTENSION IF NOT EXISTS vector" 2>$null
Write-Host "  pgvector extension enabled" -ForegroundColor DarkGreen

& $pgCtl stop -D $pgDataDir -w

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Cyan
Write-Host "  PostgreSQL: tools\pgsql\bin\pg_ctl.exe" -ForegroundColor Green
Write-Host "  Data:       tools\pgsql-data\" -ForegroundColor Green
Write-Host "  Database:   hindsight_dev (pgvector enabled)" -ForegroundColor Green
Write-Host "  Start:      devstack2.ps1 (automatic)" -ForegroundColor Green
