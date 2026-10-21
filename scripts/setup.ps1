param([switch]$SkipBuild)
. (Join-Path $PSScriptRoot 'common.ps1')
if (-not (Test-Path -LiteralPath $PythonExe)) {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Install uv (https://docs.astral.sh/uv/) then run setup again.' }
    & uv venv --python 3.12 (Join-Path $BackendDir '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 environment creation failed.' }
}
& uv pip install --python $PythonExe -r (Join-Path $BackendDir 'requirements.lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
if (-not (Test-Path -LiteralPath $BunExe) -or -not (Test-Path -LiteralPath $NodeExe)) {
    Push-Location -LiteralPath $AppRoot
    try { & npm.cmd install --prefix tools --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { throw 'Build tool installation failed.' } }
    finally { Pop-Location }
}
$env:PATH = (Split-Path $NodeExe) + ';' + $env:PATH
Push-Location -LiteralPath (Join-Path $AppRoot 'frontend')
try { & $BunExe install --frozen-lockfile; if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' } }
finally { Pop-Location }
Invoke-Admin -Arguments @('init')
if (-not $SkipBuild) { & (Join-Path $PSScriptRoot 'build.ps1') }
Write-Host 'Setup complete. Double-click Start-CodeTop.cmd.'
