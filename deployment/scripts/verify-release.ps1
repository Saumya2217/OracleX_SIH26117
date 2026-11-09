param([string]$ReleaseDirectory)

. (Join-Path $PSScriptRoot "common.ps1")
if (-not $ReleaseDirectory) { $ReleaseDirectory = Get-OracleXRoot }
$ReleaseDirectory = (Resolve-Path $ReleaseDirectory).Path
Test-ReleaseChecksums $ReleaseDirectory
Write-Host "All release checksums are valid."
