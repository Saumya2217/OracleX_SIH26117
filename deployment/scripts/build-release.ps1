param(
    [string]$OutputDirectory,
    [switch]$ApplicationOnly
)

. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-OracleXRoot
$releaseVersion = "1.5.0"
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $root "deployment\release\OracleX-$releaseVersion"
}
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)

Assert-Command "docker"
Assert-Command "python"
Assert-Command "npm"

$requiredModelFiles = @("model.gguf", "model.sha256", "MODEL-LICENSE.txt", "model-source.json", "Modelfile")
if (-not $ApplicationOnly) {
    foreach ($name in $requiredModelFiles) {
        $path = Join-Path $root "deployment\model\$name"
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -eq 0) {
            throw "Complete release requires approved model artifact: $path"
        }
    }
    Push-Location (Join-Path $root "deployment\model")
    try {
        $checkLine = Get-Content -LiteralPath "model.sha256" -Raw
        if ($checkLine -notmatch '^([0-9a-fA-F]{64})\s+\*?model\.gguf\s*$') {
            throw "model.sha256 must contain '<sha256>  model.gguf'."
        }
        $actualModelHash = (Get-FileHash -Algorithm SHA256 -LiteralPath "model.gguf").Hash
        if ($actualModelHash -ne $Matches[1]) {
            throw "Approved model checksum does not match model.sha256."
        }
    } finally {
        Pop-Location
    }
}

$frontend = Join-Path $root "frontend"
$backend = Join-Path $root "backend"
$wheelhouse = Join-Path $backend "wheelhouse"
if (Test-Path -LiteralPath $wheelhouse) { Remove-Item -LiteralPath $wheelhouse -Recurse -Force }
New-Item -ItemType Directory -Path $wheelhouse | Out-Null

Push-Location $frontend
try {
    & npm ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
} finally {
    Pop-Location
}

& python -m pip download --require-hashes --only-binary=:all: `
    --platform manylinux_2_28_x86_64 --platform manylinux2014_x86_64 `
    --implementation cp --python-version 3.11 --abi cp311 `
    --dest $wheelhouse -r (Join-Path $backend "requirements.lock")
if ($LASTEXITCODE -ne 0) { throw "Linux wheelhouse download or hash verification failed." }

$lock = Get-Content -LiteralPath (Join-Path $root "deployment\artifacts.lock.json") -Raw | ConvertFrom-Json
foreach ($artifact in $lock.artifacts) {
    $immutable = "$($artifact.reference)@$($artifact.digest)"
    & docker pull --platform linux/amd64 $immutable
    if ($LASTEXITCODE -ne 0) { throw "Failed to pull pinned image $immutable" }
    & docker tag $immutable $artifact.reference
    if ($LASTEXITCODE -ne 0) { throw "Failed to tag pinned image $immutable" }
}

& docker build --network=none --pull=false --platform linux/amd64 -t "oraclex/backend:$releaseVersion" $backend
if ($LASTEXITCODE -ne 0) { throw "Offline backend image build failed." }
& docker build --network=none --pull=false --platform linux/amd64 -t "oraclex/frontend:$releaseVersion" $frontend
if ($LASTEXITCODE -ne 0) { throw "Offline frontend image build failed." }

if (Test-Path -LiteralPath $OutputDirectory) { Remove-Item -LiteralPath $OutputDirectory -Recurse -Force }
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
New-Item -ItemType Directory -Path (Join-Path $OutputDirectory "images") | Out-Null
Copy-Item -LiteralPath (Join-Path $root "docker-compose.yml") -Destination $OutputDirectory
Copy-Item -LiteralPath (Join-Path $root ".env.example") -Destination $OutputDirectory
Copy-Item -LiteralPath (Join-Path $root "README.md") -Destination $OutputDirectory
New-Item -ItemType Directory -Path (Join-Path $OutputDirectory "deployment") | Out-Null
Copy-Item -LiteralPath (Join-Path $root "deployment\scripts") -Destination (Join-Path $OutputDirectory "deployment") -Recurse
Copy-Item -LiteralPath (Join-Path $root "deployment\artifacts.lock.json") -Destination (Join-Path $OutputDirectory "deployment")
New-Item -ItemType Directory -Path (Join-Path $OutputDirectory "deployment\model") | Out-Null
if (-not $ApplicationOnly) {
    foreach ($name in $requiredModelFiles) {
        Copy-Item -LiteralPath (Join-Path $root "deployment\model\$name") -Destination (Join-Path $OutputDirectory "deployment\model")
    }
}

& python (Join-Path $PSScriptRoot "generate-dependency-inventory.py") $wheelhouse (Join-Path $frontend "node_modules") (Join-Path $OutputDirectory "dependency-inventory.json")
if ($LASTEXITCODE -ne 0) { throw "Dependency inventory generation failed." }

$images = @(
    "oraclex/backend:$releaseVersion",
    "oraclex/frontend:$releaseVersion",
    "postgres:15.15-alpine3.23",
    "ollama/ollama:0.34.1"
)
& docker save --output (Join-Path $OutputDirectory "images\oraclex-images.tar") @images
if ($LASTEXITCODE -ne 0) { throw "Docker image export failed." }

$manifest = [ordered]@{
    product = "OracleX"
    version = $releaseVersion
    built_at_utc = [DateTime]::UtcNow.ToString("o")
    platform = "linux/amd64"
    complete = -not [bool]$ApplicationOnly
    network_policy = "runtime compose network is internal"
    images = $images
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $OutputDirectory "release-manifest.json") -Encoding utf8

$files = Get-ChildItem -LiteralPath $OutputDirectory -File -Recurse | Where-Object Name -ne "SHA256SUMS" | Sort-Object FullName
$checksumLines = foreach ($file in $files) {
    $relative = [IO.Path]::GetRelativePath($OutputDirectory, $file.FullName).Replace('\', '/')
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
    "$hash *$relative"
}
$checksumLines | Set-Content -LiteralPath (Join-Path $OutputDirectory "SHA256SUMS") -Encoding ascii
Test-ReleaseChecksums $OutputDirectory
Write-Host "Verified offline release created at $OutputDirectory"

