. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Python
Push-Location -LiteralPath $AppRoot
try {
    & $PythonExe -m pytest -c backend/pytest.ini backend/tests -q --tb=short
    if ($LASTEXITCODE -ne 0) { throw 'Backend verification failed.' }
    & $NodeExe --test frontend/tests/*.test.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Frontend request verification failed.' }
    Push-Location -LiteralPath (Join-Path $AppRoot 'frontend')
    try {
        & $NodeExe node_modules/typescript/bin/tsc -b
        if ($LASTEXITCODE -ne 0) { throw 'Frontend type-check failed.' }
    } finally { Pop-Location }
} finally { Pop-Location }
Write-Host 'Verification passed. Test artifacts were retained.'
