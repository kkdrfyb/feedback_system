param(
  [string]$EnvName = "feedback-system-dev",
  [string]$BundleDir = "offline_bundle"
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$bundle = Join-Path $root $BundleDir
$wheels = Join-Path $bundle "wheels"
$dist = Join-Path $bundle "dist"

New-Item -ItemType Directory -Force -Path $bundle | Out-Null
New-Item -ItemType Directory -Force -Path $wheels | Out-Null
New-Item -ItemType Directory -Force -Path $dist | Out-Null

Write-Host "Downloading Python wheels..."
conda run -n $EnvName python -m pip download -r (Join-Path $root "requirements.txt") -d $wheels

Write-Host "Building frontend..."
Push-Location (Join-Path $root "frontend")
npm install
npm run build
Pop-Location

Copy-Item -Path (Join-Path $root "frontend\\dist\\*") -Destination $dist -Recurse -Force

Copy-Item -Path (Join-Path $root "requirements.txt") -Destination (Join-Path $bundle "requirements.txt") -Force
Copy-Item -Path (Join-Path $root "backend\\requirements.txt") -Destination (Join-Path $bundle "backend-requirements.txt") -Force
Copy-Item -Path (Join-Path $root "start_offline.bat") -Destination (Join-Path $bundle "start_offline.bat") -Force
Copy-Item -Path (Join-Path $root "scripts\\install_offline.ps1") -Destination (Join-Path $bundle "install_offline.ps1") -Force

Write-Host "Offline bundle ready at: $bundle"
