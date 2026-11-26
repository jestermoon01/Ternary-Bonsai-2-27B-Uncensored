# Ternary Bonsai local deployments

This repository contains two local deployments:

- [`bonsai-local`](./bonsai-local/README.md): Bonsai 2 27B with its uncensored LoRA.
- [`bonsai25-local`](./bonsai25-local/README.md): Bonsai 2.5 27B.
- [`bonsai25-uncensored-local`](./bonsai25-uncensored-local/README.md): Bonsai 2.5 with its uncensored LoRA.

The model weights and Bonsai 2.5 adapter are Apache-2.0 licensed; see
[`licenses/`](./licenses/). The Bonsai 2 AtomicChat adapter is fetched from its
upstream Hugging Face repository by the setup script and is not mirrored here.
The deployment scripts/configuration have no separate license declaration.

## Download models

The GGUF models are not stored in this repository. Each setup script downloads
the required model files from their pinned Hugging Face revisions and verifies
their sizes and SHA256 checksums:

```powershell
git clone https://github.com/jestermoon01/Ternary-Bonsai-2-27B-Uncensored.git
cd .\Ternary-Bonsai-2-27B-Uncensored\bonsai-local
.\scripts\setup.ps1
```

Model downloads require about 6 GB per deployment and are stored locally under
each deployment's `models` directory.

## Run a deployment

Run the setup script from the deployment directory. For example:

```powershell
cd .\bonsai-local
.\scripts\setup.ps1
.\scripts\start.ps1
```

The Bonsai 2.5 uncensored compose file uses the 2.5 model and adapter from
`bonsai25-local\models`; run `bonsai25-local\scripts\setup.ps1` first, then
start the compose file from the repository root:

```powershell
docker compose -f .\bonsai25-uncensored-local\compose.yaml up -d --wait --wait-timeout 600
```

Only one deployment should occupy the GPU at a time; the compose configurations
use the same loopback port.
