$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose stop
if ($LASTEXITCODE -ne 0) { throw 'Could not stop Bonsai' }
if (Test-Path .qwen-paused) {
    docker start qwen-local-inference-1
    if ($LASTEXITCODE -ne 0) { throw 'Could not restore Qwen' }
    Remove-Item -LiteralPath .qwen-paused
    Write-Host 'Qwen is starting again at http://localhost:8001/'
}
