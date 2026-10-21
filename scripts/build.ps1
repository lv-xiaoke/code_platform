. (Join-Path $PSScriptRoot 'common.ps1')
if (-not (Test-Path -LiteralPath $NodeExe)) { throw 'Node 24 build tool missing. Run scripts/setup.ps1.' }
$ReleaseName = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + ([guid]::NewGuid().ToString('N').Substring(0,6))
$ReleaseRelative = 'releases/' + $ReleaseName
$ReleasePath = Join-Path $AppRoot $ReleaseRelative
New-Item -ItemType Directory -Path $ReleasePath | Out-Null
$env:PATH = (Split-Path $NodeExe) + ';' + $env:PATH
Push-Location -LiteralPath (Join-Path $AppRoot 'frontend')
try {
    & $NodeExe 'node_modules/typescript/bin/tsc' -b
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript check failed; current release retained.' }
    & $NodeExe 'node_modules/vite/bin/vite.js' build --outDir $ReleasePath --emptyOutDir false
    if ($LASTEXITCODE -ne 0) { throw 'Build failed; current release retained.' }
}
finally { Pop-Location }
if (-not (Test-Path -LiteralPath (Join-Path $ReleasePath 'index.html'))) { throw 'Built index.html missing.' }
$Manifest = @{ path = $ReleaseRelative; built_at = (Get-Date).ToString('o'); version = '1.1.0' } | ConvertTo-Json
$PendingManifest = Join-Path $AppRoot ('releases/current-' + $ReleaseName + '.json')
Set-Content -LiteralPath $PendingManifest -Value $Manifest -Encoding UTF8
$Current = Join-Path $AppRoot 'releases/current.json'
if (Test-Path -LiteralPath $Current) {
    $Previous = Join-Path $AppRoot ('releases/previous-' + $ReleaseName + '.json')
    [System.IO.File]::Replace($PendingManifest,$Current,$Previous)
} else { Move-Item -LiteralPath $PendingManifest -Destination $Current }
Write-Host "Release ready: $ReleasePath"
