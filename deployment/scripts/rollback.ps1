param(
    [Parameter(Mandatory = $true)][string]$PreviousReleaseDirectory,
    [Parameter(Mandatory = $true)][string]$BackupDirectory,
    [Parameter(Mandatory = $true)][string]$Confirmation
)

if ($Confirmation -ne "ROLLBACK-ORACLEX") { throw "Pass -Confirmation ROLLBACK-ORACLEX to continue." }
. (Join-Path $PSScriptRoot "common.ps1")
$currentRoot = Get-OracleXRoot
$PreviousReleaseDirectory = (Resolve-Path $PreviousReleaseDirectory).Path
Test-ReleaseChecksums $PreviousReleaseDirectory
Copy-Item -LiteralPath (Join-Path $currentRoot ".env") -Destination (Join-Path $PreviousReleaseDirectory ".env") -Force
Invoke-OracleXCompose -Root $currentRoot -Arguments @("stop")
& (Join-Path $PreviousReleaseDirectory "deployment\scripts\install.ps1") -SkipModelImport
if ($LASTEXITCODE -ne 0) { throw "Previous release could not be started." }
& (Join-Path $PreviousReleaseDirectory "deployment\scripts\restore.ps1") -BackupDirectory $BackupDirectory -Confirmation "RESTORE-ORACLEX"
if ($LASTEXITCODE -ne 0) { throw "Rollback data restore failed." }
Write-Host "Rollback completed."
