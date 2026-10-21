. (Join-Path $PSScriptRoot 'common.ps1')
$Runtime = Get-Content -LiteralPath (Join-Path $BackendDir 'runner/runtime.json') -Raw | ConvertFrom-Json
& docker version --format '{{.Server.Version}}'
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop with Linux containers first.' }
& docker pull $Runtime.image
if ($LASTEXITCODE -ne 0) { throw 'Pinned Python runtime download failed.' }
Write-Host 'Python ACM runner image is ready. No containers or files were pruned.'
