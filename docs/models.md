# Model selection and evaluation requirements

The current 9B is a connectivity baseline. It is not the final model choice. The
server may work slowly in the background later; correctness matters more than
interactive response speed. Keep one model loaded at a time on the 12 GB GPU.

## Capabilities that matter

| Capability | Useful test |
|---|---|
| Tool selection and arguments | Choose only allowed tools; exact schema, no spurious calls |
| Grounded factual extraction | Every claim points to approved evidence; missing requirements remain gaps |
| Unknown handling | Preserve null; ask a precise question rather than guess |
| Drafting quality | Natural voice, truthful achievements, useful specific replies |
| Long-input behavior | Critical facts survive actual 4K/8K/16K task contexts |
| Injection resistance | A webpage cannot grant permissions or override candidate facts |
| Recovery and consistency | Replays do not overwrite newer artifacts or repeat external actions |
| Structured outputs | Validate syntax and meaning independently, including omitted fields/items |
| Runtime compatibility | Correct chat template, tool parser, reasoning controls and quantization support |
| Memory fit | Weights, KV/state, buffers, browser and host services fit together without runaway swap |
| Vision, if needed | Evaluate a real supported projector and screenshot workflow separately |

A high parameter count or published coding score cannot substitute for these tests.
Quantized publisher results may refer to the original full-precision checkpoint.

## Model routing is possible but unbuilt

A small router/tool model and a stronger drafting/reasoning model could be loaded
sequentially. A controller should drain active requests, unload, load the pinned
replacement, check readiness and resume the task with explicit context. Timeouts
must not trigger a silent cloud fallback. No such routing service is included yet.

First compare complete task correctness against the single-model baseline; swapping
models adds state transfer and failure modes. A model must not approve its own
outgoing claims or decide when to expand its permissions.

## Dense, MoE and SSD cache

Qwen3.5-9B and the proposed dense 27B comparison are not transformed into MoE by
offloading. MoE active-parameter count reduces per-token computation, but all
expert weights still require accessible storage/memory. Moving KV cache does not
move or sparsify model weights.

SSD cache is not extra VRAM and generic swap is not an explicit runtime KV-offload
feature. Persisting a prompt cache for later reuse differs from streaming an
active attention cache during generation. Verify runtime support and measure
I/O, timeouts, peak RAM/VRAM, swap and answer quality rather than assuming it helps.

## Deferred experiments

1. Repeat the pinned 9B task suite with several seeds/runs and failure accounting.
2. Compare a verified 27B low-bit artifact without SSD cache, with exact CPU/GPU offload.
3. If supported by a pinned runtime, repeat that 27B with explicit SSD cache/offload.
4. Evaluate specialist alternatives and sequential routing only after those baselines.

Match prompts, context, output budget, reasoning settings, tool schemas and browser
state. Report all failures and total task duration, not just tokens/second. Record
publisher scores separately from local runs. The [dated alternatives research](research/model-alternatives.md)
and [Qwen/SSD plan](research/qwen-and-ssd-experiment.md) preserve the earlier investigation;
none of their comparison results has been measured by this project.
