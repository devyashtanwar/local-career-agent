> Historical research snapshot, 14 November 2026. Sources and recommendations below reflect that investigation; no referenced third-party project is bundled or runtime-validated by this repository. Later setup/results: [current findings](../findings.md). Recheck mutable upstream links before reuse.


# Local model alternatives — Hugging Face research

## Decision

There are credible candidates that outperform Qwen3.5-9B on selected publisher-reported agent benchmarks while having quantized weights appropriate for investigating on the RTX 3060 12 GB / 16 GB RAM PC. There is no verified universal winner over Qwen3.8-27B Q3 on this hardware. No model was installed or benchmarked during this research. Existing benchmark A/B/C remains agreed; these are candidates for the next comparison, not silent replacements.

Recommended next candidate: **Ornith-1.5-9B Q4_K_M if screenshot-based browser use is required; NeoHorse-1-9B Q4_K_M for text/DOM-only tool workflows.** The highest-upside separate experiment is **Ternary Bonsai 2 27B**, whose weights are much smaller than conventional 27B Q3, but whose runtime and tool-call limitations need testing before use in account workflows.

The previous blanket implication that any 27B model must need roughly 11–13 GB at low precision is incomplete: model-specific ternary compression offers a different memory/quality tradeoff. This does not convert the dense model into MoE.

## Evidence and deployable artifacts

All GB values below are decimal **file sizes**, not total runtime memory. Actual fit depends on cache, buffers, context and browser activity. Start with one model, short context, text-only tests; then add vision/browser workload. A public model card is evidence of a reported result, not independent validation or proof that Q4 preserves it.

| Candidate | Verified artifact | Evidence relevant to this task | Material qualification |
| --- | --- | --- | --- |
| NeoHorse-1-9B | Publisher Q4_K_M **5.63 GB**; Q5_K_M 6.47 GB | In its own comparison: BFCL v4 67.43 vs Qwen 64.88; PinchBench 82.25 vs 74.55; VitaBench 42.25 vs 31.25 | Text-only release. IFEval slightly lower, 89.09 vs 89.46. Quantization compatibility checks are not quality benchmarks. |
| Ornith-1.5-9B | Publisher Q4_K_M **5.78 GB**; optional BF16 vision projector **0.92 GB** | Its card reports MCP-Atlas 54.2 vs Qwen 46.8; Toolathlon 41.2 vs 29.6; GPQA 86.4 vs 81.7 | Preserve its chat template/reasoning/tool parser. Published evaluations use large contexts and expensive scaffolds; the PC's short-context deployment is a different condition. |
| MiMo-V2.6-Distill-Qwen-9B | Community Q4_K_M **5.63 GB** | Publisher comparison: AutomationBench 30.3 vs 5.0; Toolathlon 35.2 vs 25.9; JobBench 18.3 vs 2.6 | SFT research checkpoint, dedicated MiMo template/parser. JobBench measures professional work, not job-application acceptance. Community GGUF needs functional validation. |
| Nanbeige4.2-3B | Community Q4_K_M **2.68 GB** | Card reports MCP-Atlas 57.8 vs Qwen 47.4, Pinch-Bench-V2 74.7 vs 68.2, GPQA 87.4 vs 81.7 | Name counts non-embedding parameters: about 4B total. Looped architecture; small weights do not establish low latency. Custom runtime branch required in current card. |
| Gemma 4 12B Instruct | Community Q4_K_M **7.12 GB** | Google reports LiveCodeBench v6 72.0; Qwen card reports 65.6. Native vision/audio and function calling provide an alternative architecture | These scores are across separate cards, not a controlled comparison. Google GPQA 78.8 and Tau2 69.0 do not establish a general win over Qwen. Keep as a multimodal alternative, not the first tool-agent challenger. |

Primary cards: [NeoHorse](https://huggingface.co/TokenRhythm/NeoHorse-1-9B), [Ornith](https://huggingface.co/ornith-ai/Ornith-1.5-9B), [MiMo](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B), [Nanbeige](https://huggingface.co/Nanbeige/Nanbeige4.2-3B), [Gemma](https://huggingface.co/google/gemma-4-12B-it). Each Qwen comparison above uses the baseline in that publisher's table, rather than mixing baseline numbers from other reports.

Artifact sources: [NeoHorse publisher GGUF](https://huggingface.co/TokenRhythm/NeoHorse-1-9B-GGUF), [Ornith publisher GGUF](https://huggingface.co/ornith-ai/Ornith-1.5-9B-GGUF), [MiMo community GGUF](https://huggingface.co/prithivMLmods/MiMo-V2.6-Distill-Qwen-9B-GGUF), [Nanbeige community GGUF](https://huggingface.co/bartowski/Nanbeige_Nanbeige4.2-3B-GGUF), [Gemma community GGUF](https://huggingface.co/unsloth/gemma-4-12b-it-GGUF).

The NeoHorse GGUF card explicitly says published scores are from the original checkpoint. Its eight short 4K compatibility checks cover tool calls and continuation, but LM Studio and Ollama quantized variants were not separately tested by the publisher. Native vision files are absent. Ornith's publisher repository does include a projector; vision accuracy and full runtime memory still need a local test. Do not advertise a text-only model as a replacement for a screenshot-dependent browser configuration.

## Most consequential discovery: Ternary Bonsai 2 27B

[Publisher model and benchmarks](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf), [runtime formats](https://docs.prismml.com/download/formats), [known issues](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/KNOWN_ISSUES.md).

Derived from Qwen3.8-27B. Verified model files: **PTQ1_0 5.95 GB**, **PQ2_0 7.21 GB**, **Q2_0 7.63 GB**. Optional vision projector is additional. It remains dense. Specialized ternary representation is not equivalent to applying an arbitrary ordinary 2-bit quantization to the original checkpoint.

In Prism's own matched 14-benchmark suite, the original FP16 model averages **86.32**, Bonsai **84.78**, ordinary IQ2_XXS **72.59**, and UD-Q4_K_XL **85.18**. Its reported BFCL v3 is 74.92 vs FP16 76.74. The headline 98.2% is a ratio of aggregate benchmark scores, not a guarantee of 98.2% of every capability or job-task reliability. No direct Q3 comparison was established here.

PTQ1_0/PQ2_0 require Prism's runtime kernels. Q2_0 needs a sufficiently recent upstream runtime with the model's activation transform support; official pages disagree on the minimum build (b11555 versus b11556), so use a pinned known-good build and validate outputs. Merely recognizing the file's quantization type is insufficient. Do not place these files into the existing LM Studio installation and assume correctness.

Its known-issues page explicitly reports malformed/looping tool calls, empty/truncated responses, reasoning-budget behavior and CUDA-build issues. Some runtime docs and the older known-issues page disagree about reasoning controls. Test the exact build's behavior. The published throughput table does not measure this RTX 3060; do not transfer figures from an A100, RTX 4090 or Apple laptop. No speed prediction is claimed.

**Inference:** this is a higher-value memory-fit experiment than assuming SSD cache streaming is necessary for any usable 27B. It may retain strong quality with headroom on the PC; runtime fit, latency and tool reliability remain hypotheses.

## Genuine small MoE and other screened choices

[LiquidAI LFM2.5-8B-A1B](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B) is a genuine small MoE: 8.3B total / 1.5B active. Its publisher Q4_K_M is **5.16 GB**. It is a credible speed/headroom candidate with tool-oriented training and broad runtime support. Its reported BFCL v4 is around 49 and the card cautions against heavy programming and knowledge-intensive use without retrieval. No evidence supports calling it a general quality upgrade over Qwen3.5-9B. Native calls are Pythonic unless configured otherwise; test the adapter.

[ZAYA1-8B](https://huggingface.co/Zyphra/ZAYA1-8B) is another actual compact MoE (8.4B total / 760M active), with strong reasoning claims. It did not yield enough directly relevant tool/browser evidence to prioritize over the shortlist.

[O2-9B Preview](https://huggingface.co/ant-intl/O2-9b-preview) improves several scores but regresses BFCL v4 (51.83 versus its Qwen baseline 62.36); not the first choice for a reliability-led tool assistant. [Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B) is a compact research candidate, but large agent/scaffold results should not be read as proof of a drop-in local win. Larger GLM/Nemotron/Qwen MoEs are not automatically good fits merely because their active parameter counts are small; total weights and host memory still count. Specialized math/coding scores alone do not establish resume factuality or safe browser execution.

## Research limits and next action

Exa discovery: 55 returned search-result slots across eight queries (duplicates present), followed by primary-card/runtime reads. HF API metadata was checked for seven quantization repositories, preserving revisions, byte sizes and hashes in the workspace snapshot. One supplementary check verified vision files and the Liquid model size. Research cutoff: 14 November 2026. Publisher benchmarks, custom scaffolds and quantizer claims were kept distinct from local measurements. No external model code or installation instructions were executed.

Recommended small extension to the agreed experiment: after the Qwen 9B baseline, compare **Ornith 9B Q4** for the browser-capable role and **NeoHorse 9B Q4** for text tool work; then test **Bonsai 2 27B PQ2_0 or the verified stock-compatible Q2_0 build** as the memory-efficient 27B challenger. Keep Nanbeige/MiMo/Gemma as reserve candidates rather than expanding immediately to an exhaustive benchmark run. Keep exact model formats and runtime builds separate in results. The normal 27B with/without SSD comparison remains documented and unexecuted.

**Produced:** sourced shortlist, runtime caveats, verified artifact metadata and a prioritized test decision. **Unknown:** actual latency, task correctness and full browser memory fit on the PC. **Resume point:** establish the current 9B baseline on the PC, then run the first chosen challenger; no default model or setup script was changed.
