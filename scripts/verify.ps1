. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Python
Push-Location -LiteralPath $AppRoot
try {
    & $PythonExe -m pytest -c backend/pytest.ini backend/tests -q --tb=short
    if ($LASTEXITCODE -ne 0) { throw 'Backend verification failed.' }
    & $NodeExe --test frontend/tests/acm-requests.test.mjs frontend/tests/catalog-controls.test.mjs frontend/tests/practice-session.test.mjs frontend/tests/problem-entry.test.mjs frontend/tests/console-output.test.mjs frontend/tests/terminal.test.mjs frontend/tests/ai.test.mjs frontend/tests/code-history.test.mjs frontend/tests/runner-environment.test.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Frontend request verification failed.' }
    Push-Location -LiteralPath (Join-Path $AppRoot 'frontend')
    try {
        & $NodeExe node_modules/typescript/bin/tsc -b
        if ($LASTEXITCODE -ne 0) { throw 'Frontend type-check failed.' }
    } finally { Pop-Location }
} finally { Pop-Location }
Write-Host 'Verification passed. Test artifacts were retained.'
