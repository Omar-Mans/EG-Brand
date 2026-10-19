# Adds the settings that are missing from backend\.env (taken from backend\.env.example).
# Never changes or removes a value you already set. Run from the project folder:
#   powershell -ExecutionPolicy Bypass -File scripts\update-env.ps1
$root = Split-Path -Parent $PSScriptRoot
$example = Join-Path $root "backend\.env.example"
$target = Join-Path $root "backend\.env"

if (-not (Test-Path $target)) {
    Copy-Item $example $target
    Write-Host "Created backend\.env - open it and fill in your keys."
    exit 0
}

$have = @{}
foreach ($line in Get-Content $target) {
    if ($line -match '^\s*([A-Z0-9_]+)\s*=') { $have[$Matches[1]] = $true }
}
$missing = @()
foreach ($line in Get-Content $example) {
    if ($line -match '^\s*([A-Z0-9_]+)\s*=' -and -not $have.ContainsKey($Matches[1])) { $missing += $line }
}

if ($missing.Count -eq 0) {
    Write-Host "backend\.env already has every setting."
} else {
    Add-Content -Path $target -Value ""
    Add-Content -Path $target -Value "# --- added by scripts/update-env.ps1 on $(Get-Date -Format yyyy-MM-dd)"
    Add-Content -Path $target -Value $missing
    Write-Host "Added $($missing.Count) settings to backend\.env:"
    $missing | ForEach-Object { Write-Host "  $_" }
}
