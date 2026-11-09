Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-OracleXRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not on PATH."
    }
}

function Assert-EnvironmentFile([string]$Root) {
    $path = Join-Path $Root ".env"
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing $path. Copy .env.example to .env and replace every placeholder before starting OracleX."
    }
    $content = Get-Content -LiteralPath $path -Raw
    if ($content -match "replace-with-") {
        throw ".env still contains placeholder values."
    }
    return $path
}

function Invoke-OracleXCompose {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    Assert-Command "docker"
    $envFile = Assert-EnvironmentFile $Root
    & docker compose --project-directory $Root --env-file $envFile -f (Join-Path $Root "docker-compose.yml") @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed with exit code $LASTEXITCODE."
    }
}

function Test-ReleaseChecksums([string]$Root) {
    $checksumPath = Join-Path $Root "SHA256SUMS"
    if (-not (Test-Path -LiteralPath $checksumPath)) {
        throw "Missing SHA256SUMS in release directory."
    }
    foreach ($line in Get-Content -LiteralPath $checksumPath) {
        if (-not $line.Trim()) { continue }
        if ($line -notmatch '^([0-9a-fA-F]{64}) \*(.+)$') {
            throw "Invalid checksum entry: $line"
        }
        $expected = $Matches[1].ToLowerInvariant()
        $relative = $Matches[2].Replace('/', [IO.Path]::DirectorySeparatorChar)
        $file = Join-Path $Root $relative
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Release artifact is missing: $relative"
        }
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash.ToLowerInvariant()
        if ($actual -ne $expected) {
            throw "Checksum mismatch: $relative"
        }
    }
}
