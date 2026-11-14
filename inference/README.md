# Inference bootstrap

Start with [the repository runbook](../docs/setup.md). This folder preserves the
tested standard-library Python bootstrap and its 13 regression tests.

```bash
python3 setup_pc.py                     # prerequisite checks only
python3 setup_pc.py --apply             # explicit download/install/load and checks
python3 setup_pc.py --check             # checks an already-running matching API
python3 -m unittest discover -s . -p 'test_*.py'
```

Run as a normal user on x86_64 Omarchy/Arch. NVIDIA driver, 12 GB GPU, approximately
16 GB RAM, free memory/storage and system-library checks are enforced. The script
does not install OS packages, change SSH/firewall/swap or update the driver.

The default model is `qwen35-9b`. Optional pinned download definitions for
`qwen3-14b` and `qwen35-4b` are included in `models.json`; they were not benchmarked
by this pilot. Each artifact has repository revision, exact byte count and SHA-256.
Q4_K_M is mixed-bit quantization, not four bits for every tensor. File size is not
total runtime memory. No vision projector or screenshot capability is installed.

`--apply` downloads and verifies the official LM Studio headless installer when
needed, imports the verified GGUF by symbolic link, resolves its unique registered
model key, estimates loading and uses full GPU offload at 4K context. Existing
servers or loaded models block setup rather than being taken over.

Two API checks exercise grounded skill extraction and queuing unknown work
authorization through a tool call. They use `reasoning_effort=none` and a small
output budget. The script checks output semantics for these fixtures, not just
JSON validity. They do not validate arbitrary application answers. The later
OpenClaw gateway task failed a related factual check; see [findings](../docs/findings.md).

Reports and verified downloads live at
`${XDG_DATA_HOME:-$HOME/.local/share}/career-assistant`. `local-model.env` is generated
only if both smoke checks pass. Its API key is a placeholder, not authentication.
API requests bypass proxy variables and reject redirects. Downloads need internet.

Failures retain artifacts for inspection and perform best-effort cleanup of the
model/server this invocation attempted to start. The lightweight daemon may remain.
Cleanup errors are recorded. Never run two setup invocations concurrently.
Run `lms server stop`, `lms unload MODEL_ALIAS` and `lms daemon down` when finished.

Changing the installer upstream invalidates the pinned digest. Inspect the new
source and deliberately update the pin; do not disable verification. An existing
runtime is reused, so a hash-pinned installer does not certify its current version.
Record actual runtime versions from the report.

The headless runtime was selected for straightforward single-user GGUF loading and
memory controls, not a measured speed advantage over vLLM. vLLM and direct llama.cpp
remain alternatives for a separately pinned, measured comparison. No vLLM setup or
27B/SSD-cache implementation is provided here.

Primary references: [headless runtime](https://lmstudio.ai/docs/developer/core/headless),
[load controls](https://lmstudio.ai/docs/cli/local-models/load),
[vLLM installation](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/).
