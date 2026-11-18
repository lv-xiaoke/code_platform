param([switch]$SkipBuild,[switch]$RuntimeOnly,[switch]$BuildFromSource)
. (Join-Path $PSScriptRoot 'common.ps1')
if ($RuntimeOnly -and ($BuildFromSource -or $SkipBuild)) { throw 'RuntimeOnly cannot be combined with BuildFromSource or SkipBuild.' }
$ManifestPath = Join-Path $AppRoot 'releases/current.json'
if (-not $BuildFromSource -and -not $SkipBuild -and (Test-Path -LiteralPath $ManifestPath)) { $RuntimeOnly = $true }
if ($RuntimeOnly -and -not (Test-Path -LiteralPath $ManifestPath)) { throw 'Prebuilt frontend missing. Use the Windows release ZIP or run setup.ps1 -BuildFromSource.' }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is required for installation. Install uv from https://docs.astral.sh/uv/getting-started/installation/ then reopen the terminal and run Setup-CodeTop.cmd.'
}
$Snapshot = Join-Path $AppRoot 'vendor/algoTop-main/public/data/codetop.json'
if (-not (Test-Path -LiteralPath $Snapshot)) { throw 'Built-in catalog missing: vendor/algoTop-main/public/data/codetop.json. Download the complete source or release ZIP.' }
if (-not $RuntimeOnly -and (-not (Test-Path -LiteralPath $BunExe) -or -not (Test-Path -LiteralPath $NodeExe)) -and -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'Source builds require npm. Install Node.js (with npm), or use the prebuilt Windows release ZIP.'
}
Write-Host "Installing CodeTop in: $AppRoot"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    & uv venv --python 3.12 (Join-Path $BackendDir '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 environment creation failed.' }
}
& $PythonExe -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'The existing backend/.venv must use Python 3.12. Install into a new directory; keep the old data for backup.' }
& uv pip install --python $PythonExe -r (Join-Path $BackendDir 'requirements.lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed. Check network access to the Python package index and retry.' }
if (-not $RuntimeOnly) {
    if (-not (Test-Path -LiteralPath $BunExe) -or -not (Test-Path -LiteralPath $NodeExe)) {
        Push-Location -LiteralPath $AppRoot
        try { & npm.cmd install --prefix tools --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { throw 'Build tool installation failed.' } }
        finally { Pop-Location }
    }
    $env:PATH = (Split-Path $NodeExe) + ';' + $env:PATH
    Push-Location -LiteralPath (Join-Path $AppRoot 'frontend')
    try { & $BunExe install --frozen-lockfile; if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' } }
    finally { Pop-Location }
}
Invoke-Admin -Arguments @('init')
if (-not $RuntimeOnly -and -not $SkipBuild) { & (Join-Path $PSScriptRoot 'build.ps1') }
Write-Host 'Setup complete. Double-click Start-CodeTop.cmd.'
