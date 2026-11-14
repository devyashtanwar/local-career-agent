> Historical research snapshot, 14 November 2026. Sources and recommendations below reflect that investigation; no referenced third-party project is bundled or runtime-validated by this repository. Later setup/results: [current findings](../findings.md). Recheck mutable upstream links before reuse.


# Qwen 9B Q4 versus Qwen 3.8 27B Q3 — Comparison

**Actual execution status:** neither model has been benchmarked on the target PC in this session. Last confirmed PC state was powered off. No tokens/second, latency, peak memory or quantized task-accuracy results are available. This note compares published evidence and identifies the exact experiment needed.

Target: Omarchy, RTX 3060 12 GB VRAM, i5-12400F, 16 GB system RAM. Existing setup defaults to Qwen3.5-9B Q4_K_M and full GPU offload. **That script has not been changed to load 27B:** full offload is not an established safe setting for this candidate.

## Published model scores — contextual evidence only

| Benchmark | Qwen3.5-9B | Qwen3.8-27B |
| --- | ---: | ---: |
| GPQA Diamond — scientific reasoning | 81.7 | 89.2 |
| IFBench — instruction following | 64.5 | 79.5 |
| LiveCodeBench v6 — coding | 65.6 | 90.3 |

Sources: [Qwen3.5-9B official card](https://huggingface.co/Qwen/Qwen3.5-9B), [Qwen3.8-27B official card](https://huggingface.co/Qwen/Qwen3.8-27B).

These are publisher-reported scores for the released models, not measurements of the requested Q4/Q3 artifacts. The cards do not establish a controlled head-to-head with identical inference settings. They support treating 27B as a serious quality candidate, not claiming its 3-bit version retains those scores or a specific reduction in job-application errors. Both are dense models.

## Quantization choice changes feasibility

| Artifact | Listed weights, decimal GB | Inference for this PC |
| --- | ---: | --- |
| Qwen3.5-9B Q4_K_M | 5.68 | Much more GPU headroom for context, runtime buffers and desktop/browser activity. |
| Qwen3.8-27B UD-IQ3_XXS | 10.9 | First 27B candidate to try for GPU residency, with short context. Fits as weights alone; full runtime fit unverified. |
| Qwen3.8-27B UD-IQ3_S | 12.0 | Very tight once buffers/cache/display use are included; partial CPU offload may be needed. |
| Qwen3.8-27B UD-Q3_K_XL | 13.1 | Weights alone exceed 12 GiB (approximately 12.88 decimal GB); requires offloading or more VRAM. |

Sources: [9B GGUF listings](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF), [27B GGUF listings](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF). Values are rounded listings, not allocated VRAM. Three-bit is a family of formats; these artifacts are not interchangeable. Mixed precision and metadata mean parameter count times nominal bit width is not an exact file-size calculation.

**Hypothesis:** 27B offers better difficult-task reasoning, but 9B completes browser loops faster and with more memory margin on this PC. Quantization loss, runtime kernels and CPU offload can change that outcome. Do not assume 27B is exactly three times slower or that the old 30B MoE benchmark predicts this dense model's speed. System RAM and VRAM are separate pools, not a single interchangeable 28 GB allocation.

## The hardware comparison to run

Default exact pair: 9B Q4_K_M versus 27B UD-IQ3_XXS. Add UD-Q3_K_XL as an optional CPU/GPU split trial if the smaller 3-bit artifact loses too much quality. Before downloading, pin the 27B repository revision and artifact hash, as done for existing setup candidates.

Use the same installed LM Studio runtime build, one loaded model at a time, text only, the same 4,096-token context, identical prompts, temperature and output budget. Explicitly disable thinking for both where the runtime supports that setting and verify it took effect. Compare thinking mode separately; Qwen3.8 defaults to deep reasoning, which would otherwise confound latency. Record actual GPU offload layers and cache settings; do not force identical full-offload settings when one model cannot fit.

Use 30 fixed synthetic career tasks, repeated three times per model: ten fact/skill extraction and missing-answer cases, ten structured/tool-call cases, five untrusted-page instruction cases, and five resume/social drafting cases. Keep the expected factual answers fixed before running. Assess drafts blind against the same rubric; do not let a model grade its own writing as the only evidence. These cases are a proposed local evaluation, not an existing validated benchmark dataset.

Perform one excluded warm-up per model. Measure cold load separately. Record first-token latency, complete task latency (median and p95), output tokens/second with its definition, peak VRAM, process/system RAM, swap activity, correct facts, schema/tool correctness, unwanted actions and crashes. Sample memory during inference rather than using an after-the-fact snapshot as a claimed peak. Retain failures and timeouts. Then repeat a small subset with the normal browser workload open. Do not reuse the earlier two-prompt smoke test as a general model benchmark.

## Provisional decision and resume point

Keep **9B Q4 as the working default** pending measurements. Test **27B Q3 as the quality challenger**, particularly for occasional harder review/drafting tasks. Do not enable a second simultaneously resident model on this hardware. If 27B improves task correctness enough to justify latency without swapping or exhausting browser memory, promote it for the tasks it wins. Otherwise retain it as an optional slower reviewer or stay with 9B.

**Next:** bring the PC online, establish the existing 9B baseline, then run the exact-pair comparison with recorded offload settings. This is the current resume point; no new runtime or model download occurred for this comparison.


## Follow-up: SSD cache and treating dense 27B as MoE

**Finding:** offloading can extend memory capacity, but it cannot turn this pretrained dense model into a mixture of experts. [Qwen3.8-27B's official card](https://huggingface.co/Qwen/Qwen3.8-27B) identifies it as dense, with hybrid linear/full attention. Its layers' dense computations still run for each token; there is no trained expert router selecting a small active expert subset. Moving layers between RAM and GPU is possible in supported runtimes, but that is device placement/streaming, with associated computation or transfer cost. Sparse expert selection requires an actual MoE architecture or substantial model transformation/training with quality evaluation.

Separate three allocations: model weights, attention cache/recurrent state, and temporary computation buffers. Moving cache off the GPU only reduces the cache allocation. It does not shrink weights or remove the need for working buffers. For this hybrid model, cache/state sizing must reflect its actual architecture; a generic full-attention cache formula is misleading.

**SSD caching is real:** [vLLM's offloading connector](https://docs.vllm.ai/en/latest/features/kv_offloading_usage/) stores completed KV blocks in slower tiers and promotes cache hits to GPU on demand. Its filesystem tier supports persistent storage. [LMCache's storage documentation](https://docs.lmcache.ai/kv_cache/storage_backends/local_storage.html) also describes disk storage and prefetching into CPU memory, although that specific page documents deprecated in-process mode. These are not proof of ready compatibility with the selected GGUF/LM Studio runtime or this model's hybrid state.

The key distinction is storing cold/reusable prefixes or inactive sessions versus keeping an active generation's entire working cache on disk. Cold-cache reuse can avoid repeated prompt computation. Active attention data still must be accessed where computation runs; repeatedly fetching it from SSD trades capacity for transfer latency and bandwidth. It is not equivalent to adding VRAM, and OS swap is not an optimized inference cache. [Transformers' cache documentation](https://huggingface.co/docs/transformers/en/kv_cache) describes CPU-RAM offloading with layer-by-layer prefetch and a throughput tradeoff; that generic feature does not establish support for every hybrid model/runtime.

**Recommendation for the PC experiment:** try 27B UD-IQ3_XXS at short context first; measure weights, cache/state, buffers, peak RAM/VRAM and swap. Then test supported quantized cache settings, and CPU cache or partial layer offload if needed. Treat SSD prefix/session caching as a later experiment only if measured repeated-prefix work justifies it. Do not add active SSD streaming to the default setup or promise MoE-like speed. With only 16 GB system RAM, holding all 27B quantized weights, host-side state, the operating system and the browser simultaneously may also be tight; moving cache to disk does not eliminate this constraint.

No runtime settings or scripts were changed, and no offloading performance test was run for this follow-up.


## Agreed experiment: three comparison runs

the operator approved testing both 27B approaches against the 9B baseline. Interpretation: 9B is the reference model, not a subset of parameters activated inside 27B.

| Run | Model | Cache policy |
| --- | --- | --- |
| A — reference | Qwen3.5-9B Q4_K_M | In-memory cache; no SSD cache tier |
| B — 27B baseline | Qwen3.8-27B UD-IQ3_XXS initially | In-memory cache; no SSD cache tier |
| C — SSD experiment | Exact same 27B artifact as B | SSD-backed cache tier, verified by backend metrics and disk reads/writes |

Use the same synthetic tasks and scoring for all three. For B versus C hold runtime build, weight quantization, context, thinking mode, output limit and weight offload placement constant for the controlled comparison. Keep the CPU cache budget and ordinary GPU prefix-cache policy matched as far as the backend permits. If enabling SSD caching requires a different runtime than the initial LM Studio baseline, rerun B in that same runtime; do not attribute cross-runtime differences to SSD caching. A later capacity-optimized comparison may change settings, but label it separately.

Run first-use prompts and repeated-prefix requests separately. Report cache hits, actual bytes loaded/stored, first-token and total latency, generation rate with its definition, peak VRAM/RAM, swap, disk activity and task correctness. SSD-file creation alone does not prove a beneficial disk-cache hit. OS page cache can satisfy filesystem reads from RAM, so distinguish storage-tier hits from observed physical SSD I/O. Do not drop system-wide caches or enable swap merely to manufacture an SSD-backed result.

**Compatibility gate:** the SSD run remains pending a supported backend for this exact hybrid model and quantization. The current setup script has no SSD-cache switch. [vLLM's offloading guide](https://docs.vllm.ai/en/latest/features/kv_offloading_usage/) describes CPU staging, filesystem secondary tiers and hybrid-state constraints; support must be demonstrated, not inferred from a generic setting. Its documented prefix-cache offloading does not by itself prove active-generation context expansion. Report repeated-prefix reuse and any demonstrated active-cache capacity extension as distinct outcomes. If unsupported or memory-limited, record that result rather than substituting ordinary OS swap.

Status: experiment agreed and documented; no runs executed. Next action: bring the PC online and establish A before provisioning the matched 27B B/C backend.
