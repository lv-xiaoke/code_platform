param([int]$Port=8000)
. (Join-Path $PSScriptRoot 'common.ps1')
try { $Health = Invoke-RestMethod "http://127.0.0.1:$Port/api/v1/health" -TimeoutSec 2 } catch { Write-Host "No reachable CodeTop service on port $Port."; return }
if ($Health.app -ne 'codetop-local' -or $Health.root -ne $AppRoot) { throw 'The port belongs to another application; no process stopped.' }
$ServiceProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($Health.process_id)"
$BasePython = (& $PythonExe -c 'import json,sys; print(json.dumps(sys._base_executable))') | ConvertFrom-Json
if (-not $ServiceProcess -or $ServiceProcess.ExecutablePath -notin @($PythonExe,$BasePython) -or $ServiceProcess.CommandLine -notmatch '(?:\s-m\s+app\.serve(?:\s|$)|\sapp\.main:app(?:\s|$))') { throw 'Service process identity could not be verified; no process stopped.' }
Stop-Process -Id $Health.process_id
for ($Try=0;$Try -lt 50;$Try++) {
    if (-not (Get-Process -Id $Health.process_id -ErrorAction SilentlyContinue)) { Write-Host 'CodeTop stopped.'; return }
    Start-Sleep -Milliseconds 200
}
throw 'The service has not stopped yet. Restore has not been started.'
