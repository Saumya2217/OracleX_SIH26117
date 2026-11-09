param([switch]$SkipModelImport)

. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-OracleXRoot
Test-ReleaseChecksums $root
Assert-Command "docker"

$imageArchive = Join-Path $root "images\oraclex-images.tar"
if (-not (Test-Path -LiteralPath $imageArchive)) { throw "Missing image archive: $imageArchive" }
& docker load --input $imageArchive
if ($LASTEXITCODE -ne 0) { throw "Docker image import failed." }

if (-not (Test-Path -LiteralPath (Join-Path $root ".env"))) {
    Copy-Item -LiteralPath (Join-Path $root ".env.example") -Destination (Join-Path $root ".env")
    throw "Created .env. Replace every placeholder, set the approved origin and rerun install.ps1."
}
Assert-EnvironmentFile $root | Out-Null
Invoke-OracleXCompose -Root $root -Arguments @("up", "-d", "postgres", "ollama")
if (-not $SkipModelImport) {
    Invoke-OracleXCompose -Root $root -Arguments @("--profile", "model-tools", "run", "--rm", "model-import")
}
Invoke-OracleXCompose -Root $root -Arguments @("up", "-d")
Write-Host "OracleX installation is running. Check /health/ready through the configured company URL."
