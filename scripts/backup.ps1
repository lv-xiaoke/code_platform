param([string]$DataDir='')
. (Join-Path $PSScriptRoot 'common.ps1')
if (-not $DataDir) { $DataDir = Join-Path $AppRoot 'data' }
Invoke-Admin -Arguments @('backup','--data-dir',[System.IO.Path]::GetFullPath($DataDir))
