param([int]$Port=8000,[switch]$NoBrowser,[string]$DataDir='')
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Python
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Port must be between 1024 and 65535.' }
if (-not $DataDir) { $DataDir = Join-Path $AppRoot 'data' }
$DataDir = [System.IO.Path]::GetFullPath($DataDir)
$Url = "http://127.0.0.1:$Port"
$Listener = New-Object System.Net.Sockets.TcpClient
$Occupied = $false
try { $Task = $Listener.ConnectAsync('127.0.0.1',$Port); $Occupied = $Task.Wait(400) -and $Listener.Connected } catch { } finally { $Listener.Dispose() }
if ($Occupied) {
    try { $Health = Invoke-RestMethod "$Url/api/v1/health" -TimeoutSec 3 } catch { throw "Port $Port is occupied by another program." }
    if ($Health.app -ne 'codetop-local' -or $Health.root -ne $AppRoot -or $Health.data_dir -ne $DataDir) { throw "Port $Port belongs to a different application or data directory." }
    Write-Host "CodeTop is already running: $Url"
    if (-not $NoBrowser) { Start-Process $Url }
    return
}
if (-not (Test-Path -LiteralPath (Join-Path $AppRoot 'releases/current.json'))) { throw 'Frontend build missing. Run scripts/build.ps1.' }
$RuntimeDir = Join-Path $AppRoot 'runtime'
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$LogStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$StdoutLog = Join-Path $RuntimeDir "server-$Port-$LogStamp.log"
$StderrLog = Join-Path $RuntimeDir "server-$Port-$LogStamp.err.log"
$env:CODETOP_DATA_DIR = $DataDir
$Arguments = @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$Port",'--workers','1','--no-access-log')
$Process = Start-Process -FilePath $PythonExe -ArgumentList $Arguments -WorkingDirectory $BackendDir -WindowStyle Hidden -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog -PassThru
for ($Attempt=0; $Attempt -lt 150; $Attempt++) {
    try {
        $Health = Invoke-RestMethod "$Url/api/v1/health" -TimeoutSec 1
        if ($Health.app -eq 'codetop-local' -and $Health.root -eq $AppRoot -and $Health.data_dir -eq $DataDir) {
            Write-Host "CodeTop ready: $Url"
            Write-Host "Log: $StderrLog"
            if (-not $NoBrowser) { Start-Process $Url }
            return
        }
    } catch { }
    if ($Process.HasExited) { throw "Service stopped before becoming healthy. See $StderrLog" }
    Start-Sleep -Milliseconds 400
}
throw "Startup timed out. See $StderrLog"
