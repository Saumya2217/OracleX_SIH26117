$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"
$frontendModules = Join-Path $frontendDir "node_modules"

if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing .env. Copy .env.example to .env and replace every placeholder secret."
}
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Missing backend virtual environment. Follow the setup steps in README.md."
}
if (-not (Test-Path -LiteralPath $frontendModules)) {
    throw "Missing frontend dependencies. Run npm ci in the frontend directory."
}

Push-Location $backendDir
try {
    & $pythonExe -c "from app.services.vector_store import vector_store_service; vector_store_service.client.heartbeat()"
    if ($LASTEXITCODE -ne 0) { throw "Start the configured local Chroma server first; see README.md." }
    & $pythonExe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed. The application was not started." }
} finally { Pop-Location }

$backend = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $backendDir `
    -WindowStyle Hidden `
    -PassThru

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1
        if ($health.status -eq "live") {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $ready) {
    Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
    throw "The OracleX backend did not become ready within 30 seconds."
}

$worker = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList "-m", "app.workers.ingestion" `
    -WorkingDirectory $backendDir `
    -WindowStyle Hidden `
    -PassThru

$frontend = Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $frontendDir `
    -WindowStyle Hidden `
    -PassThru

Write-Host "OracleX development services started."
Write-Host "Application: http://127.0.0.1:5173"
Write-Host "API docs:    http://127.0.0.1:8000/docs"
Write-Host "Backend PID: $($backend.Id)"
Write-Host "Worker PID:  $($worker.Id)"
Write-Host "Frontend PID: $($frontend.Id)"
