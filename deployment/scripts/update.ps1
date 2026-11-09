param(
    [Parameter(Mandatory = $true)][string]$NewReleaseDirectory,
    [string]$BackupDirectory
)

. (Join-Path $PSScriptRoot "common.ps1")
$currentRoot = Get-OracleXRoot
$NewReleaseDirectory = (Resolve-Path $NewReleaseDirectory).Path
Test-ReleaseChecksums $NewReleaseDirectory
if (-not $BackupDirectory) {
    $BackupDirectory = Join-Path $currentRoot ("backups\pre-update-" + [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmssZ"))
}
& (Join-Path $PSScriptRoot "backup.ps1") -DestinationDirectory $BackupDirectory
if ($LASTEXITCODE -ne 0) { throw "Pre-update backup failed." }

$currentEnv = Join-Path $currentRoot ".env"
$newEnv = Join-Path $NewReleaseDirectory ".env"
Copy-Item -LiteralPath $currentEnv -Destination $newEnv -Force
Invoke-OracleXCompose -Root $currentRoot -Arguments @("stop")
& (Join-Path $NewReleaseDirectory "deployment\scripts\install.ps1")
if ($LASTEXITCODE -ne 0) { throw "New release installation failed. Use rollback.ps1 with the previous release and the backup at $BackupDirectory." }
Write-Host "Update completed. Retain the previous release and backup until verification is complete."
