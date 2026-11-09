param(
    [Parameter(Mandatory = $true)][string]$BackupDirectory,
    [Parameter(Mandatory = $true)][string]$Confirmation
)

. (Join-Path $PSScriptRoot "common.ps1")
if ($Confirmation -ne "RESTORE-ORACLEX") { throw "Pass -Confirmation RESTORE-ORACLEX to acknowledge replacement of current data." }
$root = Get-OracleXRoot
$BackupDirectory = (Resolve-Path $BackupDirectory).Path
$databaseDump = Join-Path $BackupDirectory "database.dump"
$uploads = Join-Path $BackupDirectory "uploads"
if (-not (Test-Path -LiteralPath $databaseDump) -or -not (Test-Path -LiteralPath $uploads)) {
    throw "Backup must contain database.dump and uploads."
}

Assert-Command "docker"
$envFile = Assert-EnvironmentFile $root
$compose = @("compose", "--project-directory", $root, "--env-file", $envFile, "-f", (Join-Path $root "docker-compose.yml"))
& docker @compose stop frontend backend worker
& docker @compose up -d postgres
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL could not be started for restore." }
$databaseContainer = (& docker @compose ps -q postgres).Trim()
& docker cp $databaseDump "${databaseContainer}:/tmp/oraclex.dump"
if ($LASTEXITCODE -ne 0) { throw "Could not copy database backup into PostgreSQL." }
& docker @compose exec -T postgres sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/oraclex.dump'
if ($LASTEXITCODE -ne 0) { throw "Database restore failed." }

& docker @compose up -d backend
if ($LASTEXITCODE -ne 0) { throw "Backend could not be started for upload restore." }
$backendContainer = (& docker @compose ps -q backend).Trim()
& docker @compose exec -T backend sh -c 'find /app/data/uploads -mindepth 1 -maxdepth 1 -exec rm -rf {} +'
if ($LASTEXITCODE -ne 0) { throw "Could not clear the upload volume before restore." }
& docker cp (Join-Path $uploads ".") "${backendContainer}:/app/data/uploads"
if ($LASTEXITCODE -ne 0) { throw "Upload restore failed." }
& docker @compose run --rm --no-deps backend python -m app.workers.reconcile --repair
if ($LASTEXITCODE -ne 0) { throw "Restored document/index reconciliation found unresolved errors." }
& docker @compose up -d
if ($LASTEXITCODE -ne 0) { throw "OracleX did not restart after restore." }
Write-Host "Restore completed from $BackupDirectory"
