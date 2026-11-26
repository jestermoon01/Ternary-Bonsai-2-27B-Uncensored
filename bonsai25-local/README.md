# Local PrismML Ternary Bonsai 2.5 27B

Independent Docker Compose service on the RTX 5070 12 GB, using the official
`Ternary-Bonsai-2.5-27B-PTQ1_0-mtp.gguf`. Both the 6,232,818,944-byte GGUF
and PrismML CUDA 12.8 runtime release `prism-b12232-f702476` are revision-pinned
and SHA256 verified. The setup script downloads them from their pinned sources;
the model weights are not included in this repository. See `model-manifest.json`.

This is the official 2.5 model with its built-in MTP head. The older AtomicChat
Bonsai 2 adapter is not applied to this different checkpoint.

## Start and connect

From `C:\Users\PC\Desktop\Artex\bonsai25-local` in PowerShell:

```powershell
# Already completed; rerun for file verification and image build.
.\scripts\setup.ps1

# Stops Qwen inference/gateway and old Bonsai if running, then starts 2.5.
.\scripts\start.ps1

# Stops Bonsai; leaves Qwen stopped.
.\scripts\stop.ps1
```

Chat UI: **http://localhost:8003/**

OpenAI-compatible base URL: **http://localhost:8003/v1**

Model: **bonsai-2.5-27b**. No API key required; host port binds to Windows
loopback. One active request, 32,768-token context, all layers on GPU, flash
attention, F16 K/V caches, 8 CPU threads, 512-token batch, 128-token microbatch.
MTP uses one draft token per pass with a 0.1 probability cutoff. Thinking uses
the model's default; disable it per request for direct answers.

```python
import json
import urllib.request

body = {
    'model': 'bonsai-2.5-27b',
    'messages': [{'role': 'user', 'content': 'Explain binary search briefly.'}],
    'max_tokens': 512,
    'chat_template_kwargs': {'enable_thinking': False},
}
req = urllib.request.Request(
    'http://127.0.0.1:8003/v1/chat/completions',
    data=json.dumps(body).encode(),
    headers={'Content-Type': 'application/json'},
)
with urllib.request.urlopen(req, timeout=120) as response:
    print(json.load(response)['choices'][0]['message']['content'])
```

Use a larger output budget when thinking is enabled: reasoning consumes output
tokens before the answer. Qwen/ARTEX connections on port 8001 are stopped;
they have not been redirected to this API. This deployment has no Mem0 gateway
or automatic context compression. The service is left running after testing,
but has no automatic restart policy to avoid GPU conflicts after reboot.

To switch back explicitly:

```powershell
.\scripts\stop.ps1
docker start qwen-local-inference-1 qwen-local-gateway-1
```

## Reproduce the performance comparison

```powershell
python .\scripts\benchmark.py --label mtp1 --full

# Same model and hardware settings, MTP disabled.
$env:SPEC_TYPE = 'none'
docker compose up -d --wait --wait-timeout 600
python .\scripts\benchmark.py --label plain

# Return to the default MTP configuration.
Remove-Item Env:SPEC_TYPE
docker compose up -d --wait --wait-timeout 600
```

The script warms the server, then runs three real prompts twice: coding and
math with thinking enabled, and prose with thinking disabled. Each measured
run generates exactly 1,024 tokens, intentionally ending at the output limit.
Those capped generations measure throughput; they do not demonstrate complete,
correct answers or reproduce the community author's 54-task quality score.
Greedy sampling and seed 42 are used in both modes. Results contain the full
requests and responses, backend prompt/decode timings, wall time, token usage,
finish reason, draft counts and acceptance, server properties, and GPU samples.
The full suite also checks arithmetic, code recall at both ends of an 18K-token
input, and SSE streaming. GPU samples are approximately once a second, include
desktop usage, and may miss transient peaks.

Reference community report: [133 tokens/s, one-token MTP, 89% acceptance,
RTX 5070 12 GB, 32K context](https://www.reddit.com/r/LowEndLocalAI/comments/1y5tr51/surprising_results_5_local_models_on_an_rtx_5070/).
Its exact prompts, runtime command, and cache format are not supplied. Our
Linux CUDA 12.8 container also differs from the author's unspecified Windows
runtime setup. Therefore this is an independent check of the headline speed,
not an exact reproduction of the original experiment.

Sources: [official model](https://huggingface.co/prism-ml/Ternary-Bonsai-2.5-27B-GGUF),
[PrismML MTP documentation](https://github.com/PrismML-Eng/Bonsai-demo/blob/main/SPECULATIVE.md),
[runtime release](https://github.com/PrismML-Eng/llama.cpp/releases/tag/prism-b12232-f702476).

The Docker image uses the existing CUDA 12.8 base for its system libraries,
but runs exclusively from `/runtime` so the PrismML backend loader does not
mix its shared libraries with the base image's older llama.cpp libraries.

## Measurements on this PC, 2026-11-26

The 100+ tokens/s headline was reproduced; the specific 133 tokens/s result was
not reproduced on these prompts and this runtime. Median decode speed with
one-token MTP was 115.15 tokens/s, 13.4% below the reported 133. The matching
plain-decoding median was 78.19 tokens/s: a **1.47x** MTP speedup.

| Workload | One-token MTP, two runs | Plain, two runs |
| --- | ---: | ---: |
| Coding, thinking on | 114.73 / 115.56 tokens/s | 77.10 / 78.54 tokens/s |
| Math, thinking on | 117.67 / 117.58 tokens/s | 76.62 / 78.23 tokens/s |
| Prose, thinking off | 107.99 / 107.36 tokens/s | 78.69 / 78.14 tokens/s |

Each row's runs generated 1,024 output tokens. Rates above exclude prompt
processing; the JSON also records end-to-end rates. Thinking tokens count
toward generated tokens. Overall draft acceptance was 82.84% (2,780 of 3,356),
versus the community report's 89%; math reached 89.44%, prose 74.11%.

Arithmetic returned `703`. Long-input recall returned both boundary codes
correctly from 18,043 prompt tokens: 13.47 seconds prompt processing and
13.81 seconds total for a 16-token answer. SSE streaming completed with first
content at 1.05 seconds. Sampled GPU usage peaked at 9,904 MiB (9.67 GiB),
including desktop use. The 32K slot initialized successfully; 18,043 prompt
tokens were the longest inference input tested.

Full evidence: `results/mtp1.json`, `results/plain.json`,
`results/comparison.json`, and the two server logs. Bonsai 2.5 was left running
with MTP enabled; Qwen inference and gateway were left stopped as requested.
