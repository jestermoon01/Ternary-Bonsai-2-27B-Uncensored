$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$manifest = Get-Content -Raw model-manifest.json | ConvertFrom-Json
New-Item -ItemType Directory -Force models,downloads,results | Out-Null
foreach ($kind in @('model', 'runtime')) {
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
$adapterPath = Join-Path models $manifest.adapter.filename
if (-not (Test-Path -LiteralPath $adapterPath) -or
    (Get-Item -LiteralPath $adapterPath).Length -ne $manifest.adapter.size) {
    $adapterUrl = "https://huggingface.co/$($manifest.adapter.repository)/resolve/$($manifest.adapter.revision)/$($manifest.adapter.filename)"
    & curl.exe -L --fail --retry 3 --continue-at - --output $adapterPath $adapterUrl
    if ($LASTEXITCODE -ne 0) { throw 'Download failed: uncensored adapter' }
}
if ((Get-Item -LiteralPath $adapterPath).Length -ne $manifest.adapter.size -or
    (Get-FileHash -LiteralPath $adapterPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.adapter.sha256) {
    throw "Checksum mismatch: $adapterPath"
}
docker compose build
if ($LASTEXITCODE -ne 0) { throw 'Runtime image build failed' }
