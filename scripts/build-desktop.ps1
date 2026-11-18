param([switch]$SkipFrontend,[switch]$SkipInstaller)
. (Join-Path $PSScriptRoot 'common.ps1')
if (-not $SkipFrontend) { & (Join-Path $PSScriptRoot 'build.ps1') }
$BuildPython = Join-Path $AppRoot 'runtime/desktop-work/build-env/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $BuildPython)) { throw 'Prepare the isolated desktop build environment first. See docs/deployment.md.' }
$Arguments = @((Join-Path $PSScriptRoot 'build_desktop.py'))
if ($SkipInstaller) { $Arguments += '--skip-installer' }
& $BuildPython @Arguments
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed; previous outputs retained.' }
