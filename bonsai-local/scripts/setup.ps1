$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$manifest = Get-Content -Raw model-manifest.json | ConvertFrom-Json
New-Item -ItemType Directory -Force models,downloads,runtime,results | Out-Null
foreach ($kind in @('base', 'adapter', 'runtime')) {
    $item = $manifest.$kind
    if ($kind -eq 'runtime') {
        $path = Join-Path downloads $item.filename
        $url = $item.url
    } else {
        $path = Join-Path models $item.filename
        $url = "https://huggingface.co/$($item.repository)/resolve/$($item.revision)/$($item.filename)"
    }
    if (-not (Test-Path -LiteralPath $path) -or (Get-Item -LiteralPath $path).Length -ne $item.size) {
        & curl.exe -L --fail --retry 3 --continue-at - --output $path $url
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $kind" }
    }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) {
        throw "Checksum mismatch: $path"
    }
    Write-Host "Verified $kind"
}
if ((Get-FileHash -LiteralPath (Join-Path models $manifest.adapter.filename) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.adapter.sha256) {
    throw "Checksum mismatch: $(Join-Path models $manifest.adapter.filename)"
}
docker compose build
if ($LASTEXITCODE -ne 0) { throw 'Runtime image build failed' }
Write-Host 'Files verified. Run .\scripts\start.ps1 to switch GPU inference to Bonsai.'
