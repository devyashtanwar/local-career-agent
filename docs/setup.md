# Setup and replication

This runbook reproduces the staged local baseline. It does not install an
end-to-end application or social automation service. **Use a fresh Linux user
without an existing OpenClaw configuration.** The config generator refuses to
overwrite one. Merge manually after a backup if you already use OpenClaw.

## Recorded target and prerequisites

- x86_64 Omarchy 4.0.6 / Arch Linux; Intel i5-12400F
- RTX 3060, 12,288 MiB VRAM; 16 GB host RAM; ample SSD storage
- NVIDIA driver 615.78.08 on the original host; working `nvidia-smi`
- Python 3.9+ for inference bootstrap; Bash, curl, tar, `ss`, gcc runtime libraries
- Node 24.22.1 and npm 11.19.1 on the recorded host
- Chromium at `/usr/bin/chromium` for the optional operator browser
- Rootless Docker prerequisites: `newuidmap`, `newgidmap`, working user namespaces,
  writable `XDG_RUNTIME_DIR`, and at least 65,536 subordinate IDs in both
  `/etc/subuid` and `/etc/subgid` for your own user
- Docker Buildx available for the official sandbox Dockerfile

The scripts do not provision SSH, change drivers, run an Arch upgrade, edit
subordinate-ID mappings or weaken OS protections. Resolve missing prerequisites
through the host's supported administration process. Do not add yourself to the
rootful Docker group to make this deployment work.

## 1. Clone and inspect

```bash
git clone https://github.com/devyashtanwar/local-career-agent.git
cd local-career-agent
python3 -m unittest discover -s inference -p 'test_*.py'
python3 -m unittest discover -s tests -p 'test_*.py'
```

Commands run on the target Linux PC, through visible terminals if working remotely.
Do not place credentials, a real resume or browser profile in this checkout.

## 2. Install and test inference

```bash
python3 inference/setup_pc.py
python3 inference/setup_pc.py --apply
```

The preflight changes nothing. `--apply` installs the official headless llmster
runtime if needed, verifies a pinned installer digest, downloads the exact GGUF
from `inference/models.json`, verifies size/hash, imports it and runs two local
API checks. Existing services/models are left alone and block setup. The report
is under `${XDG_DATA_HOME:-$HOME/.local/share}/career-assistant/setup-report.json`.

The initial bootstrap uses **4,096 tokens**. The later OpenClaw baseline uses
**16,384 tokens**; stop/unload before changing this rather than loading a second model:

```bash
export PATH="$HOME/.lmstudio/bin:$PATH"
lms server stop
lms unload career-qwen35-9b
lms load qwen3.5-9b --context-length 16384 --gpu max --parallel 1 --identifier career-qwen35-9b
lms server start --bind 127.0.0.1 --port 1234
```

`qwen3.5-9b` was the registered key on the recorded host. Use the bootstrap report's
`registered_model_key` if your registry assigns a different key. A GGUF storage
path is not necessarily a valid model key. After reboot, first run `lms daemon up`.

The local key `local-only` is a compatibility placeholder, **not enabled inference
authentication**. Other software on the same host may reach this loopback API.

## 3. Prepare OpenClaw and rootless Docker

```bash
bash scripts/install-openclaw.sh
bash scripts/prepare-rootless-docker.sh
python3 scripts/configure_openclaw.py
python3 scripts/configure_openclaw.py --apply
```

The installation helper uses the official npm package pinned to 2026.11.3 and the
same lifecycle-script allowlist used in the original setup. Do not enable all
dependency scripts to suppress warnings. Core CLI/agent behavior worked with this
allowlist; not every optional component was tested.

Rootless archives are from Docker's official static distribution, pinned to
29.9.3 with observed SHA-256 hashes. They are extracted below `~/career-ai`, not
system directories. The setup tool only checks prerequisites; no service is
installed. A digest mismatch must stop setup for investigation.

The config generator creates a random gateway token locally, writes the private
file as mode 600, and creates a minimal workspace. `${HOME}` in the public JSON is
a template marker; OpenClaw should receive the generated absolute paths. The
template's token marker is not a real credential. Do not copy a generated config
back to this repository. Keep the rootless daemon guard in the launchers: the
sandbox's namespace UID 0 setting must not be used against a rootful Docker daemon.

Validate with the installed version before proceeding:

```bash
export DO_NOT_TRACK=1 OPENCLAW_NO_AUTO_UPDATE=1
"$HOME/career-ai/openclaw/runtime/bin/openclaw" config validate
```

## 4. Start rootless Docker in a visible foreground terminal

```bash
bash "$HOME/career-ai/openclaw/run-rootless-docker.sh"
```

Leave that terminal open. In another target-PC terminal:

```bash
source "$HOME/career-ai/openclaw/env.sh"
docker info --format '{{json .SecurityOptions}}'
```

Expect `name=rootless`. No system Docker daemon is required. Review missing
prerequisites or errors instead of bypassing namespace, init or network controls.
The original setup had network/build-session warnings; a sandboxed browser network
has not been validated. Tool execution here uses `network: none`.

## 5. Build the release's tool image

```bash
mkdir -p "$HOME/career-ai/openclaw/sandbox-source"
curl --fail --location --proto '=https' --proto-redir '=https' \
  https://raw.githubusercontent.com/openclaw/openclaw/v2026.11.3/scripts/docker/sandbox/Dockerfile \
  -o "$HOME/career-ai/openclaw/sandbox-source/Dockerfile.official"
cat "$HOME/career-ai/openclaw/sandbox-source/Dockerfile.official"
```

Review before building. The inspected recipe starts with
`debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251`,
installs shell/Python/basic utilities, and uses a sandbox user. It has BuildKit
cache mounts. Stop if the recipe differs unexpectedly; a Git tag is not a signature.

```bash
docker build --progress=plain -t career-openclaw-sandbox:2026.11.3 \
  -f "$HOME/career-ai/openclaw/sandbox-source/Dockerfile.official" \
  "$HOME/career-ai/openclaw/sandbox-source"
```

The base is digest-pinned, but apt dependencies are not frozen; a future image
build need not be byte-identical. This is a tool image, **not a sandbox browser image**.
No model/GPU is mounted inside it: model inference stays on the host.

## 6. Run the gateway deliberately

```bash
bash "$HOME/career-ai/openclaw/run-gateway.sh"
```

In another terminal:

```bash
bash "$HOME/career-ai/openclaw/openclaw.sh" gateway health --json
bash "$HOME/career-ai/openclaw/openclaw.sh" security audit --json
```

With the gateway running, use `agent` **without `--local`**. Standalone embedded
`--local` mode refuses to share its state directory with an active gateway.

An interrupted task can resume on gateway startup even with cron off. Do not treat
a restart as a fresh reviewed task or allow it to reissue external actions. This
workflow risk is still open; start only the synthetic pilot.

## 7. Synthetic integration trial

Copy the example candidate into the otherwise empty workspace; do not replace an
existing candidate file. The sample is fictional and includes an unknown field.

```bash
test ! -e "$HOME/career-ai/workspace/tests/candidate.json" && \
  cp examples/candidate.synthetic.json "$HOME/career-ai/workspace/tests/candidate.json"
bash "$HOME/career-ai/openclaw/openclaw.sh" agent --agent main \
  --session-id synthetic-first-run --thinking off --timeout 120 \
  --message 'Read tests/candidate.json. Compare skills to React and TypeScript. Write tests/first-result.json with matching_skills, missing_skills, work_authorization and needs_review. Unknown authorization stays null and needs review. No external services.' --json
```

Independently check the saved output. Expected: React matches, TypeScript is
missing, authorization is null and review is true. A successful tool call or valid
JSON alone does not mean the answer is correct. The recorded fresh gateway test
failed this exact factual expectation. Do not keep retrying until a pass and call
that reliability. Preserve both outcomes.

## Stop and recover

Stop the gateway with Ctrl+C in its terminal. Stop only the pilot's named sandbox
container using `docker ps` then `docker stop CONTAINER_ID`. Stop the rootless
daemon with Ctrl+C. Stop inference separately:

```bash
lms server stop
lms unload career-qwen35-9b
lms daemon down
ss -ltn
```

Check that 1234, 18789, 18799 and 18801 are no longer listening. Nothing here
enables boot-time startup. Keep completed downloads and reports for diagnosis.
Never recursively delete an existing shared LM Studio/OpenClaw installation.

## Replication limits

The original scripts and staged target setup were exercised on one host. The
portable config generator is unit-tested locally; install/preparation wrappers
have syntax checks but have not been replayed as a complete fresh-PC install.
Record a clean-host replication as a separate result. Model/runtime availability,
system libraries and future package changes may still block it. Comparison models,
SSD cache offload, browser isolation, real PDFs, queues and account workflows remain
unimplemented or unevaluated. See [findings](findings.md) and [security](../SECURITY.md).

References: [LM Studio headless](https://lmstudio.ai/docs/developer/core/headless),
[OpenClaw install](https://docs.openclaw.ai/install),
[Docker rootless](https://docs.docker.com/engine/security/rootless/),
[OpenClaw Docker sandbox](https://docs.openclaw.ai/gateway/sandboxing/docker-backend).
