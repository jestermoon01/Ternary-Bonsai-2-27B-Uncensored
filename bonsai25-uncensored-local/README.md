# Bonsai 2.5 27B uncensored

This compose configuration applies the
`Ternary-Bonsai-2.5-27B-Uncensored-LoRA.gguf` adapter at scale 1.25 to the
Bonsai 2.5 base model. The setup script downloads and verifies both files from
their pinned Hugging Face revisions; neither weight file is stored in this
GitHub repository.

From the repository root, first prepare and verify the shared base model and
runtime:

```powershell
.\bonsai25-local\scripts\setup.ps1
docker compose -f .\bonsai25-uncensored-local\compose.yaml up -d --wait --wait-timeout 600
```

The uncensored service uses the same loopback port as the other deployments;
only one should run at a time. Stop it with:

```powershell
docker compose -f .\bonsai25-uncensored-local\compose.yaml down
```
