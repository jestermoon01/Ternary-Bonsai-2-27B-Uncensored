$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker image inspect bonsai-local-prism:prism-b10709-9a9394a --format '{{.Id}}'
if ($LASTEXITCODE -ne 0) { throw 'Run scripts/setup.ps1 first.' }
$qwenRunning = @(& docker ps --filter name=qwen-local-inference-1 --format '{{.Names}}') -contains 'qwen-local-inference-1'
if ($qwenRunning) {
    docker stop qwen-local-inference-1
    if ($LASTEXITCODE -ne 0) { throw 'Could not release Qwen GPU memory' }
    Set-Content -LiteralPath .qwen-paused -Value 'qwen-local-inference-1'
}
docker compose up -d --wait --wait-timeout 600
if ($LASTEXITCODE -ne 0) {
    docker compose stop
    if (Test-Path .qwen-paused) {
        docker start qwen-local-inference-1
        if ($LASTEXITCODE -eq 0) { Remove-Item -LiteralPath .qwen-paused }
    }
    throw 'Bonsai failed to start; inspect docker compose logs inference'
}
Write-Host 'Chat: http://localhost:8003/ ; API: http://localhost:8003/v1 ; model: bonsai-2-27b-uncensored'
