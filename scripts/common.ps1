$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $AppRoot 'backend'
$PythonExe = Join-Path $BackendDir '.venv\Scripts\python.exe'
$NodeExe = Join-Path $AppRoot 'tools\node_modules\node\bin\node.exe'
$BunExe = Join-Path $AppRoot 'tools\node_modules\bun\bin\bun.exe'
function Assert-Python {
    if (-not (Test-Path -LiteralPath $PythonExe)) { throw 'Python environment missing. Double-click Setup-CodeTop.cmd first (requires uv and network access).' }
}
function Invoke-Admin([string[]]$Arguments) {
    Assert-Python
    Push-Location -LiteralPath $BackendDir
    try { & $PythonExe -m app.cli @Arguments; if ($LASTEXITCODE -ne 0) { throw "Administration command failed: $Arguments" } }
    finally { Pop-Location }
}
