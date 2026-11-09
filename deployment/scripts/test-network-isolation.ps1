. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-OracleXRoot
$composeText = Get-Content -LiteralPath (Join-Path $root "docker-compose.yml") -Raw
if ($composeText -notmatch '(?ms)^networks:\s*.*?private:\s*\r?\n\s+internal:\s+true') {
    throw "Compose does not declare the runtime network as internal."
}
if ($composeText -match '(?i):latest\b|\b(apt-get|apk|npm|pip|ollama)\s+(pull|install)\b') {
    throw "Runtime compose contains an online install/pull or a floating latest tag."
}

Invoke-OracleXCompose -Root $root -Arguments @("up", "-d")
$envFile = Assert-EnvironmentFile $root
$compose = @("compose", "--project-directory", $root, "--env-file", $envFile, "-f", (Join-Path $root "docker-compose.yml"))
& docker @compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('https://example.com', timeout=5)" 2>$null
if ($LASTEXITCODE -eq 0) {
    throw "Unexpected outbound HTTPS access succeeded from the backend container."
}
Write-Host "Runtime compose is internally isolated and the live outbound probe was denied."
