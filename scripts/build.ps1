. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Python
if (-not (Test-Path -LiteralPath $NodeExe)) { throw 'Node 24 build tool missing. Run scripts/setup.ps1.' }
& $PythonExe (Join-Path $PSScriptRoot 'build_frontend.py') --node $NodeExe
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed; current release retained.' }
