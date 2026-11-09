param([string]$OutputDirectory)

. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-OracleXRoot
Assert-Command "docker"
$envFile = Assert-EnvironmentFile $root
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $root ("diagnostics\" + [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmssZ"))
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$compose = @("compose", "--project-directory", $root, "--env-file", $envFile, "-f", (Join-Path $root "docker-compose.yml"))
& docker @compose ps --all 2>&1 | Set-Content -LiteralPath (Join-Path $OutputDirectory "compose-status.txt")
& docker @compose logs --no-color --tail 500 2>&1 | Set-Content -LiteralPath (Join-Path $OutputDirectory "service-logs.txt")
& docker version 2>&1 | Set-Content -LiteralPath (Join-Path $OutputDirectory "docker-version.txt")

& docker @compose exec -T backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=10).read().decode())" 2>&1 |
    Set-Content -LiteralPath (Join-Path $OutputDirectory "readiness.json")
Write-Host "Redacted diagnostics written to $OutputDirectory. The script does not copy .env."
