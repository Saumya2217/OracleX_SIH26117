param([string]$DestinationDirectory)

. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-OracleXRoot
Assert-Command "docker"
$envFile = Assert-EnvironmentFile $root
if (-not $DestinationDirectory) {
    $DestinationDirectory = Join-Path $root ("backups\" + [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmssZ"))
}
$DestinationDirectory = [IO.Path]::GetFullPath($DestinationDirectory)
New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null

$compose = @("compose", "--project-directory", $root, "--env-file", $envFile, "-f", (Join-Path $root "docker-compose.yml"))
# Quiesce API and ingestion writes so the SQL dump and retained originals form one recovery point.
& docker @compose stop frontend backend worker
& docker @compose up -d postgres
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL could not be started for backup." }
& docker @compose create backend
if ($LASTEXITCODE -ne 0) { throw "Backend volume container could not be prepared for backup." }

& docker @compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/oraclex.dump'
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL backup failed." }
$databaseContainer = (& docker @compose ps -q postgres).Trim()
$backendContainer = (& docker @compose ps -q backend).Trim()
if (-not $databaseContainer -or -not $backendContainer) { throw "Could not resolve running OracleX containers." }
& docker cp "${databaseContainer}:/tmp/oraclex.dump" (Join-Path $DestinationDirectory "database.dump")
if ($LASTEXITCODE -ne 0) { throw "Could not copy the database backup." }
& docker cp "${backendContainer}:/app/data/uploads/." (Join-Path $DestinationDirectory "uploads")
if ($LASTEXITCODE -ne 0) { throw "Could not copy uploaded source documents." }

$entries = Get-ChildItem -LiteralPath $DestinationDirectory -File -Recurse | Sort-Object FullName
$lines = foreach ($entry in $entries) {
    $relative = [IO.Path]::GetRelativePath($DestinationDirectory, $entry.FullName).Replace('\', '/')
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.FullName).Hash.ToLowerInvariant()
    "$hash *$relative"
}
$lines | Set-Content -LiteralPath (Join-Path $DestinationDirectory "SHA256SUMS") -Encoding ascii
& docker @compose up -d
if ($LASTEXITCODE -ne 0) { throw "Backup completed, but OracleX could not be restarted." }
Write-Host "Backup completed at $DestinationDirectory"
