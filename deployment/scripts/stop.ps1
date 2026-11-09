. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-OracleXRoot
Invoke-OracleXCompose -Root $root -Arguments @("stop")
