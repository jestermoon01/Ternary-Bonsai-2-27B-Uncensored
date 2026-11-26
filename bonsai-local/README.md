# Local Ternary Bonsai 2 27B with AtomicChat LoRA

Separate Docker Compose deployment for this machine's RTX 5070 12 GB. Uses
PrismML's CUDA llama.cpp fork, the 5,946,648,928-byte PTQ1_0 base pack, and
AtomicChat's 9,683,168-byte `own42` adapter at scale **1.5**. This Hugging Face
repository contains an adapter; both files are required. All artifacts are
pinned and SHA256 verified by `scripts/setup.ps1` and `model-manifest.json`.

Sources:

- [AtomicChat adapter and runtime requirements](https://huggingface.co/AtomicChat/Ternary-Bonsai-2-27B-Uncensored-LoRA-GGUF)
- [PrismML base model](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf)
- [Verified runtime release prism-b10709-9a9394a](https://github.com/PrismML-Eng/llama.cpp/releases/tag/prism-b10709-9a9394a)

From `C:\Users\PC\Desktop\Artex\bonsai-local` in PowerShell:

```powershell
# Already completed; rerun to download/verify files and rebuild the image.
.\scripts\setup.ps1

# Releases GPU memory by stopping Qwen inference, then starts Bonsai.
.\scripts\start.ps1

# Real inference checks; writes complete requests, replies, and timings.
python .\scripts\test_inference.py

# Stops Bonsai and restarts Qwen if start.ps1 paused it.
.\scripts\stop.ps1
```

Chat UI: **http://localhost:8003/**

OpenAI-compatible API: **http://localhost:8003/v1**

Model: **bonsai-2-27b-uncensored**. No API key is required. The published port
binds to Windows loopback. Inference runs locally after setup downloads.

```python
import json
import urllib.request

body = {
    'model': 'bonsai-2-27b-uncensored',
    'messages': [{'role': 'user', 'content': 'Explain binary search briefly.'}],
    'max_tokens': 256,
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

The configuration has one 32,768-token slot, full GPU layer offload, flash
attention, Q8 K/V cache, eight CPU threads, and a 128-token microbatch. Thinking
is disabled by default for direct replies and these tests. Enable it per
request using `chat_template_kwargs: {"enable_thinking": true}` and allow a
larger output budget for reasoning. This setup does not include Qwen's Mem0
gateway or automatic context compression. Existing ARTEX/Qwen connections
continue to use port 8001; they are unavailable while Qwen inference is paused.

Only one of these model services should occupy the GPU at a time. Use the
scripts to switch. Bonsai has no automatic restart policy so rebooting Docker
does not silently start both models. If startup fails, start.ps1 stops Bonsai
and attempts to restore Qwen automatically.

`results/inference.json` stores actual inference output, usage, finish reasons,
backend prompt/decode timing, wall time, and streaming time to first content.
The checks cover arithmetic, a Python function checked on three inputs, short
prose, and recall of codes at both ends of a long input. These are smoke checks,
not a broad quality benchmark. Model-card performance claims were not reproduced.

## Measured on this PC, 2026-11-26

All four non-streaming checks and the streaming check passed with the adapter
active at scale 1.5, temperature 0, and thinking disabled:

| Check | Result | Wall time | Backend decode |
| --- | --- | ---: | ---: |
| Arithmetic | `37 * 19 = 703` | 0.54 s | 32.67 tokens/s (4 output tokens) |
| Python | Correct `sum_even` on three input cases | 1.03 s | 44.61 tokens/s (29 tokens) |
| Short explanation | Coherent CPU/GPU comparison | 4.36 s | 44.91 tokens/s (176 tokens) |
| Long input | Both boundary codes recalled from 19,546 prompt tokens | 36.00 s | 38.51 tokens/s (16 tokens) |
| Streaming | Exact reply and final SSE marker received | 0.90 s | First content at 0.84 s |

Long-input prompt processing took 35.42 s (551.90 tokens/s). Sampled total GPU
usage was approximately 7.5 GB; this includes desktop usage and is not a peak
measurement. Short replies give less reliable throughput estimates. The 32K
slot initialized successfully; the longest inference input tested was 19,546
tokens. Qwen was restored after testing, and Bonsai was stopped. Start Bonsai
using `scripts/start.ps1` before connecting to port 8003.
