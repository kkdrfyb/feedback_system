param(
  [string]$EnvName = "feedback-system-dev",
  [string]$BundleDir = "offline_bundle"
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$bundle = Join-Path $root $BundleDir
$wheels = Join-Path $bundle "wheels"
$dist = Join-Path $bundle "dist"
$frontendDist = Join-Path $root "frontend\\dist"

if (!(Test-Path $wheels)) {
  Write-Host "Missing wheels directory: $wheels"
  exit 1
}

Write-Host "Creating conda environment: $EnvName"
conda create -n $EnvName python=3.11 -y

Write-Host "Installing Python dependencies from offline wheels..."
conda run -n $EnvName python -m pip install --no-index --find-links $wheels -r (Join-Path $root "requirements.txt")

if (Test-Path $dist) {
  New-Item -ItemType Directory -Force -Path $frontendDist | Out-Null
  Copy-Item -Path (Join-Path $dist "*") -Destination $frontendDist -Recurse -Force
  Write-Host "Frontend dist copied to: $frontendDist"
} else {
  Write-Host "Frontend dist not found in bundle: $dist"
}

Write-Host "Offline install complete."
