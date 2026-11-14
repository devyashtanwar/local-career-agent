# Research archive

Research cutoff: 14 November 2026. These are historical investigation notes,
not maintained rankings, new runtime measurements or endorsements of every project.
Mutable links, licenses and version-specific behavior need rechecking before use.

- [Implementation reuse audit](reuse-audit.md): LangHire, ApplyPilot, AIHawk,
  engagement drafting projects and permitted interview-practice references.
- [Local model alternatives](model-alternatives.md): publisher evidence,
  quantization/runtime caveats and a candidate shortlist.
- [Qwen and SSD experiment](qwen-and-ssd-experiment.md): proposed matched tests,
  dense vs MoE and cache distinctions; comparisons remain unexecuted.

The earlier audit recommended evaluating LangHire before implementing a full
application engine. The later executed increment installed the OpenClaw/local-model
foundation. No specialized application engine was subsequently integrated. Read
[current findings](../findings.md) for the implementation state.

Referenced third-party code is not vendored here. Its license must be checked
before cherry-picking; this repository's MIT license does not relicense it.
