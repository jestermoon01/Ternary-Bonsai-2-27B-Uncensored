$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$running = @(& docker ps --format '{{.Names}}')
foreach ($name in @('qwen-local-inference-1', 'qwen-local-gateway-1', 'bonsai-local-inference-1')) {
    if ($running -contains $name) {
        docker stop $name
        if ($LASTEXITCODE -ne 0) { throw "Could not stop $name" }
    }
}
docker compose up -d --wait --wait-timeout 600
if ($LASTEXITCODE -ne 0) { throw 'Bonsai startup failed; inspect docker compose logs' }
Write-Host 'Bonsai 2.5: http://localhost:8003/ ; API http://localhost:8003/v1 ; model bonsai-2.5-27b'
