param([switch]$SkipBuild)
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Python
if (-not $SkipBuild) { & (Join-Path $PSScriptRoot 'build.ps1') }
& $PythonExe (Join-Path $PSScriptRoot 'package_release.py') --root $AppRoot
if ($LASTEXITCODE -ne 0) { throw 'Release packaging failed. Existing releases and data were retained.' }
