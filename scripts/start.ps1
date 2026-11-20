param([int]$Port=8000,[switch]$NoBrowser,[string]$DataDir='')
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Python
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Port must be between 1024 and 65535.' }
if (-not $DataDir) { $DataDir = Join-Path $AppRoot 'data' }
$DataDir = [System.IO.Path]::GetFullPath($DataDir)
$Url = "http://127.0.0.1:$Port"
$ManifestPath = Join-Path $AppRoot 'releases/current.json'
if (-not (Test-Path -LiteralPath $ManifestPath)) { throw 'Frontend build missing. Run scripts/build.ps1.' }
$BrowserUrl = $Url
if (-not $NoBrowser) {
    $Release = (Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json).path
    $ReleaseName = [Uri]::EscapeDataString((Split-Path -Leaf $Release))
    $BrowserUrl = "$Url/?release=$ReleaseName"
}
$Listener = New-Object System.Net.Sockets.TcpClient
$Occupied = $false
try { $Task = $Listener.ConnectAsync('127.0.0.1',$Port); $Occupied = $Task.Wait(400) -and $Listener.Connected } catch { } finally { $Listener.Dispose() }
if ($Occupied) {
    try { $Health = Invoke-RestMethod "$Url/api/v1/health" -TimeoutSec 3 } catch { throw "Port $Port is occupied by another program." }
    if ($Health.app -ne 'codetop-local' -or $Health.root -ne $AppRoot -or $Health.data_dir -ne $DataDir) { throw "Port $Port belongs to a different application or data directory." }
    Push-Location -LiteralPath $BackendDir
    try { $ExpectedSchema = (& $PythonExe -c 'from app.db import SCHEMA_VERSION; print(SCHEMA_VERSION)').Trim() }
    finally { Pop-Location }
    if ($Health.schema_version -ne $ExpectedSchema) {
        throw 'Existing CodeTop uses a different database schema. Close all CodeTop tabs and stop the old service before starting this build.'
    }
    Write-Host "CodeTop is already running: $Url"
    if (-not $NoBrowser) { Start-Process $BrowserUrl }
    return
}
$RuntimeDir = Join-Path $AppRoot 'runtime'
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$LogStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$StdoutLog = Join-Path $RuntimeDir "server-$Port-$LogStamp.log"
$StderrLog = Join-Path $RuntimeDir "server-$Port-$LogStamp.err.log"
$env:CODETOP_DATA_DIR = $DataDir
$Arguments = @('-m','app.serve','--port',"$Port")
if (-not $NoBrowser) { $Arguments += '--close-with-browser' }
$Process = Start-Process -FilePath $PythonExe -ArgumentList $Arguments -WorkingDirectory $BackendDir -WindowStyle Hidden -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog -PassThru
for ($Attempt=0; $Attempt -lt 150; $Attempt++) {
    try {
        $Health = Invoke-RestMethod "$Url/api/v1/health" -TimeoutSec 1
        if ($Health.app -eq 'codetop-local' -and $Health.root -eq $AppRoot -and $Health.data_dir -eq $DataDir) {
            Write-Host "CodeTop ready: $Url"
            Write-Host "Log: $StderrLog"
            if (-not $NoBrowser) { Start-Process $BrowserUrl }
            return
        }
    } catch { }
    if ($Process.HasExited) { throw "Service stopped before becoming healthy. See $StderrLog" }
    Start-Sleep -Milliseconds 400
}
throw "Startup timed out. See $StderrLog"
