param([Parameter(Mandatory=$true)][string]$Archive,[string]$DataDir='',[int]$Port=8000,[switch]$NoRestart)
. (Join-Path $PSScriptRoot 'common.ps1')
$Archive = (Resolve-Path -LiteralPath $Archive).Path
if (-not $DataDir) { $DataDir = Join-Path $AppRoot 'data' }
$DataDir = [System.IO.Path]::GetFullPath($DataDir)
& (Join-Path $PSScriptRoot 'stop.ps1') -Port $Port
Invoke-Admin -Arguments @('restore','--archive',$Archive,'--data-dir',$DataDir)
if (-not $NoRestart) { & (Join-Path $PSScriptRoot 'start.ps1') -Port $Port -DataDir $DataDir }
