# Findings from the local pilot

Recorded 14–15 November 2026 on one Omarchy PC. These are integration results,
not a full benchmark, hiring outcome study, penetration test or general accuracy score.

## Observed environment

| Item | Recorded value |
|---|---|
| CPU | Intel i5-12400F |
| GPU | RTX 3060, 12,288 MiB VRAM |
| RAM | 16 GB |
| OS | Omarchy 4.0.6, x86_64 Linux |
| NVIDIA driver | 615.78.08 |
| LM Studio runtime | llmster 0.0.27-1; CLI commit 43d4b26 |
| OpenClaw | 2026.11.3, CLI commit 847611d |
| Node / npm | 24.22.1 / 11.19.1 |
| Rootless Docker | 29.9.3 |
| Model | Qwen3.5-9B, unsloth Q4_K_M GGUF; exact revision/hash in models.json |

## Inference bootstrap: 4K context

The initial 13 regression tests passed on the target. Two direct API smoke checks
passed with `reasoning_effort=none`: extraction in 0.580 seconds and a native tool
call in 0.866 seconds. These times include the whole request; do not compare their
derived token rate to generation-only benchmark figures.

GPU memory after inference was 5,623 MiB used / 6,332 MiB free. That is a snapshot,
not peak memory. About 11 GiB host RAM remained available and swap use was zero.
The model loaded in 1.82 seconds in the recorded 4K run.

Default thinking initially exhausted a 768-token response budget. A controlled
reasoning diagnostic completed, but no general reasoning-quality conclusion follows.
Three setup fixes were verified: accept Omarchy's actual distro ID, resolve the
registered model key from the exact artifact, and disable thinking for the small
plumbing checks. See [sanitized report](../examples/results/inference-readiness.json).

## OpenClaw integration: 16K context

The same 9B artifact was loaded with 16,384 tokens for the agent trial. A real
read/write task matched React, identified TypeScript as missing, preserved unknown
authorization as null and requested review. An outside-workspace canary read was
blocked by the file-tool restriction before OS sandboxing was introduced.

The dedicated operator browser opened a public page and returned content with the
Chromium sandbox enabled. Model browser/web tools were subsequently denied after
an audit flagged small-model web access without isolation. No authenticated profile
was imported. This does not validate a model-controlled or containerized browser.

Rootless Docker was prepared without sudo or Docker group membership. The first
sandbox task could read but not write: container UID 1000 mapped to a subordinate
host UID. Mapping namespace UID 0 to the ordinary host user fixed the write path;
workspace permissions were not loosened. A subsequent sandboxed task passed.

Live inspection confirmed `network=none`, read-only root, dropped capabilities,
no-new-privileges, 1 GiB memory limit and 128-process limit. The gateway/model remained
outside this sandbox. See [inspection](../examples/results/sandbox-verification.json).

## Two failures we are retaining

**Restart recovery:** after interruption, gateway startup resumed the old session
despite cron being disabled. It overwrote a shared test result and produced the
wrong output structure. No supported recovery-disabling switch was established;
no source patch was applied. This needs immutable run paths, reviewed recovery
and idempotent actions before account integrations.

**Fresh gateway answer:** a later independent gateway task completed its tools
but returned `missing_skills: []`, omitting required TypeScript. The assertion
failed. Unknown authorization still remained null and flagged for review. This
proves that valid JSON, tool success and a previous passing task are insufficient
to trust factual completeness. See [expected vs actual](../examples/results/final-output-validation.json).
There were no repeated retries to turn that final failure into a claimed pass.

Standalone `--local` mode also refused to run while the gateway owned its state
directory. This is a useful guard, not a model failure: use gateway mode when the
gateway is active.

## Security audit and end state

The final audit reported 0 critical, 1 warning and 2 informational findings. The
warning concerned reverse-proxy trust settings; the gateway stayed on loopback
without a reverse proxy. This is limited diagnostic evidence, not security assurance.
Gateway startup also logged a remote catalog update; no complete outbound isolation
claim is made. [Audit](../examples/results/security-audit-final.json).

All pilot services and the synthetic container were stopped. Ports 1234, 18789,
18799 and 18801 had no listeners and the rootless socket was not listening.
[Cleanup evidence](../examples/results/cleanup-verification.json).

## What has not been established

No real applications, social actions, mailbox processing, one-page PDF workflow,
phone approval service, validated restart-safe queue, 27B comparison, SSD cache
offload, challenger-model evaluation or fresh-host replay of this public package.
Additional publication-time checks are recorded in [VALIDATION.md](../VALIDATION.md).
