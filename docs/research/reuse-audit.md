> Historical research snapshot, 14 November 2026. Sources and recommendations below reflect that investigation; no referenced third-party project is bundled or runtime-validated by this repository. Later setup/results: [current findings](../findings.md). Recheck mutable upstream links before reuse.


# Existing automation projects — Reuse audit

## Finding and recommendation

There is substantial implementation to reuse. We do not need to invent a browser-driven application engine, question bank, local-model adapter, or all engagement-drafting components from scratch.

**First candidate for an isolated installation evaluation: LangHire.** Its source contains a native Ollama adapter, browser-use application workers, candidate/profile and Q&A context, resume tailoring, desktop UI, and tests. It is closer to the requested local application operator than a generic OpenClaw setup alone. This changes the implementation recommendation: evaluate a specialized engine first; keep OpenClaw as an optional coordinator for messages and exception review rather than rebuilding the application engine inside it. n8n remains optional orchestration, not another competing application loop.

**Do not connect personal accounts to an unchanged checkout.** The inspected projects have material gaps against our requirements. This is an initial source review, not a comprehensive security audit or proof that any currently installed configuration works on the target PC.

## What was actually checked

Checked repository metadata and availability for ten candidate repositories. Nine were retrievable; one was not. Of the nine, one exposed documentation/assets rather than the application implementation; the others contained implementation trees. Read their READMEs and selected files covering model providers, application loops, PDF rendering, validation, telemetry, local audio, licenses, and social reply generation. Checked LangHire's testing guide and a small recent Actions sample.

No repository was installed, no external code was executed, no model/browser benchmark ran, and no accounts were connected. A README demo, an existing test suite, and a code path are different levels of evidence; none is a measured end-to-end result on your machine. Maintainer claims such as universal coverage, undetectability, no breaches, thousands of applications, or major-company interview success are not independently verified here.

## Application operators

| Project | Concrete implementation found | Local fit and important limits | Decision |
| --- | --- | --- | --- |
| [LangHire — jaimaann/LangHire](https://github.com/jaimaann/LangHire) | Python/FastAPI + browser-use application loop, Tauri/React UI, profile/Q&A context, local memory, PDF tailoring, test suites. Native `ChatOllama` adapter in source. | MIT. Best source candidate for our local application path. Current adapter config uses 32K context; host fit remains untested. Browser instructions include Gmail OTP retrieval and account creation/reset behavior we should remove. PDF code can add pages. App has analytics and the upstream runtime also needs an outbound/privacy review. | **Evaluate first in isolation; harden before real accounts.** |
| [ApplyPilot — Pickle-Pixel/ApplyPilot](https://github.com/Pickle-Pixel/ApplyPilot) | Discovery, scoring, structured profile, tailoring, PDF generation, validation, and an actual browser-submission launcher. | AGPL-3.0. Its text-generation layer supports a local endpoint, but the submission launcher explicitly runs Claude Code. It also requests bypassed permission prompts. A local text backend therefore does not make the full pipeline local. Its dry-run is conveyed as an instruction to the browser agent and still fills a live form. | Useful pipeline/profile/validator reference. Not the unchanged local-only operator. |
| [AIHawk — feder-cr/Jobs_Applier_AI_Agent](https://github.com/feder-cr/Jobs_Applier_AI_Agent) | Full employer-form operator, site plugins, missing-info statuses, separated submit/verification logic, screenshots, outcome states, tests, and loop controls. | MIT. Current model gateway is explicitly OrcaRouter; not an established local backend. PostHog telemetry code exists. Current README says macOS can discover/score but cannot submit because the browser is unavailable there. | Strong source for submission/confirmation and plugin design; adaptation required. |
| [auto_job_apply — solankimeet518](https://github.com/solankimeet518/auto_job_apply) | Bun/Playwright/React + Ollama, Indeed form automation, profile parsing, manual-question handoff, and LinkedIn outreach implementation. | Real local-model code. No LICENSE file located in inspected tree/metadata, so copying/reuse rights need resolution. Dropdown/radio handling returns the first option when context is absent or inference fails; that violates our unknown-answer rule. Platform automation risks remain. | Reference for local answering and question escalation, not install-and-trust. |
| [JobHuntr repository — lookr-fyi/job-application-bot-by-ollama-ai](https://github.com/lookr-fyi/job-application-bot-by-ollama-ai) | Product README, setup/pricing letters, images and sample output. | The inspected default-branch tree does not expose the application engine. Current README describes cloud AI despite the repository's Ollama name. Source availability and model behavior cannot be inferred from that name. | Product reference only; **not a cherry-pick codebase** from this repository. |

Generic Easy Apply bots also exist, such as [NathanDuma's implementation](https://github.com/NathanDuma/LinkedIn-Easy-Apply-Bot), but they were not promoted into the source-audited shortlist: fixed answer dictionaries and a platform-specific form loop are narrower than our dossier, factuality, and cross-site requirements. Search discovery alone is not evidence that they currently work.

## Source findings that materially change our plan

### 1. LangHire has real local support, but needs specific corrections

In [`backend/core/llm_factory.py`](https://github.com/jaimaann/LangHire/blob/e43d8faeaabe330a42697f02404580488d12088a/backend/core/llm_factory.py), the Ollama branch uses the native browser-use `ChatOllama` path with schema-oriented output and a 32,768-token context. This is stronger evidence than a README simply mentioning Ollama. It does not establish correct behavior or acceptable latency with every small model.

In [`cli/apply_jobs.py`](https://github.com/jaimaann/LangHire/blob/e43d8faeaabe330a42697f02404580488d12088a/cli/apply_jobs.py), instructions direct the browser to open Gmail for verification codes, try account creation, and attempt password resets in some cases. Replace that behavior with an explicit human-authentication ticket. Do not give the engine your primary mailbox or account-administration authority by default.

The fetched [`backend/resume/tailor.py`](https://github.com/jaimaann/LangHire/blob/main/backend/resume/tailor.py) has explicit page-overflow/new-page handling. Therefore one-page output is not guaranteed: we need a page-count/readability gate and bounded revision, not an assumption. [`src/lib/analytics.ts`](https://github.com/jaimaann/LangHire/blob/main/src/lib/analytics.ts) contains Google Analytics event code and a telemetry switch; verify startup configuration and outbound behavior rather than trusting the local-storage claim.

Its [testing guide](https://github.com/jaimaann/LangHire/blob/main/TESTING.md) says backend unit tests mock external calls and browsers. Those tests are useful but do not demonstrate live form success. A sampled later PR integration run failed; it was a PR run, not proof that the inspected default branch is broken. No test suite was run in this investigation.

### 2. ApplyPilot separates local text generation from a hosted browser operator

[`llm.py`](https://github.com/Pickle-Pixel/ApplyPilot/blob/main/src/applypilot/llm.py) supports a local endpoint. [`apply/launcher.py`](https://github.com/Pickle-Pixel/ApplyPilot/blob/4a8d521f67f5139811c0a910ef37410f8e6d836a/src/applypilot/apply/launcher.py) separately launches Claude Code and bypasses its normal permission prompts. Treat this as a hybrid architecture unless we replace and validate the submission stage.

Its [profile example](https://github.com/Pickle-Pixel/ApplyPilot/blob/main/profile.example.json), [validator](https://github.com/Pickle-Pixel/ApplyPilot/blob/main/src/applypilot/scoring/validator.py), and [PDF renderer](https://github.com/Pickle-Pixel/ApplyPilot/blob/main/src/applypilot/scoring/pdf.py) are useful references. The validator uses structural checks and a known-skill watchlist; that is not comprehensive proof of truthful content. Its prompt also includes optional CAPTCHA-service integration, which is unnecessary for our human exception path and should not be included in the pilot.

### 3. AIHawk is now much more than a LinkedIn-only bot

Current [`apply.py`](https://github.com/feder-cr/Jobs_Applier_AI_Agent/blob/main/src/aihawk/apply.py) distinguishes filled/ready, missing information, blocked, submitted, unconfirmed, refused, and failed outcomes. It separates model form completion from the submitting control and later verification. These are valuable patterns for our existing exception design.

Current [`llm.py`](https://github.com/feder-cr/Jobs_Applier_AI_Agent/blob/69526dd62162852e2eb4b23287741044b1290d44/src/aihawk/llm.py) explicitly uses OrcaRouter; [`telemetry.py`](https://github.com/feder-cr/Jobs_Applier_AI_Agent/blob/main/src/aihawk/telemetry.py) emits usage events to PostHog. We cannot call the unchanged version private/local-only. ApplyPilot's README comparison describes an older, narrower AIHawk; that comparison should not guide our selection.

### 4. Prompting for honesty does not eliminate unsafe fallback code

The local answering prompt in auto_job_apply's [`queryEngine.js`](https://github.com/solankimeet518/auto_job_apply/blob/main/backend/queryEngine.js) returns an out-of-context marker when facts are missing. But its [`applyBot.js`](https://github.com/solankimeet518/auto_job_apply/blob/main/backend/applyBot.js) dropdown/radio function can choose the first option on missing profile or LLM failure. This demonstrates why we need to inspect execution and fallback paths, not only system prompts.

## Engagement automation projects

| Project | What exists | Useful piece and limitation |
| --- | --- | --- |
| [x-reply-agent — vishaltorc](https://github.com/vishaltorc/x-reply-agent) | Source for a macOS timeline/reply agent, persona files, scoring, reply queue, drafting, quality checks, posting, and feedback. | The requested engagement loop is represented in actual code. Reuse design ideas for rank → draft → review, persona, deduplication, and quality checks. Its posting/browser mechanisms and undetectability claims are not an endorsed access strategy. It is macOS-specific, not a drop-in for the RTX PC. README says MIT but no LICENSE file was located; resolve before copying code. |
| [Tweet Reply Generator — learn-with-santosh](https://github.com/learn-with-santosh/tweet-reply-generator) | MIT Chrome-extension source plus a local Ollama proxy and copyable reply UI. | A small, understandable example for local draft generation and copy/edit interaction. It is not a proactive feed planner or autonomous submitter. Extension permissions include access to X and localhost. Inspect and restrict proxy exposure/logging before any trial. |

The [`x-reply-agent` draft pipeline](https://github.com/vishaltorc/x-reply-agent/blob/main/packages/agent-engine/src/pipeline.ts) contains local Ollama drafting and optional cloud refinement. That optional path must stay off or be removed under our privacy requirement. Its [quality gate](https://github.com/vishaltorc/x-reply-agent/blob/main/packages/agent-engine/src/quality-gate.ts) checks style/length patterns, not factual correctness or whether you agree with the author.

Finding code for an action does not establish permission, account safety, or reliable detection avoidance. Keep our platform constraints; do not install its autonomous social-posting daemon merely because it exists. The useful reusable boundary is the selection/drafting/review layer unless an exact permitted platform integration is established.

## Interview-assistance projects

The project you remember may be from the Interview Coder/Cluely family, but the exact project and claimed major-company outcomes cannot be identified or verified from the supplied description. The investigation did find actual implementations in that category:

| Project | Evidence | Reuse decision |
| --- | --- | --- |
| [Cheating Daddy — sohzm/cheating-daddy](https://github.com/sohzm/cheating-daddy) | Electron app, screen/audio processing, live assistance. README emphasizes Gemini, but inspected `localai.js` and `native-ai-runtime.js` contain a Whisper + local llama service path. GPL-3.0. | Relevant for mock interviews and permitted assistance: audio segmentation, local transcription, conversation context, local inference, and UI notifications. Local support is code-backed, but installation/platform performance has not been tested. Do not infer it is Ollama-based just because it has local inference. |
| [Natively](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant) | Larger desktop app documenting local Ollama, on-device STT, local retrieval, meeting history, and phone-related capabilities. Implementation tree, privacy policy, and license were inspected. | Broader feature reference, but it has a custom personal-use source license, not a standard permissive open-source license. License suitability needs review before use/copying. Its privacy policy describes analytics and an automatic hosted trial when no own AI is configured, so installing and clicking Start is not proof of local-only processing. |

Sources: [Cheating Daddy local path](https://github.com/sohzm/cheating-daddy/blob/main/src/utils/localai.js), [native runtime](https://github.com/sohzm/cheating-daddy/blob/main/src/utils/native-ai-runtime.js), [Natively license](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/main/LICENSE), [Natively privacy policy](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/main/PRIVACY.md).

`pickle-com/glass` returned not-found through the connected GitHub tool. That establishes it was unavailable through that route, not that every fork or copy is unavailable. It is not an installation candidate based on this investigation. No claim that any tool secretly passed an Amazon interview was independently validated. Our reusable interview components are for practice and assistance allowed by the assessment's rules, not a hidden-assistance deployment.

## Concrete reuse plan

| Need | First source to evaluate | Work we still own |
| --- | --- | --- |
| Profile, Q&A, browser application engine | LangHire | Verified dossier, unknown-answer gates, narrowly bounded actions, no automatic account administration. |
| Fixed one-page resume output | LangHire/ApplyPilot rendering ideas | Reliable page count, readability, fact/link checks, immutable packet versions. |
| Confirmed submissions and failures | AIHawk patterns | Our persisted approvals, destination/payload checks, ambiguous-outcome reconciliation. |
| Planned social engagement | x-reply-agent architecture + small local draft UI | Permitted source access, post-link/action cards, your stance, human review, no cloud refinement. |
| Interview practice | Cheating Daddy local audio pipeline, with license compliance | Consent, permitted use, host fit, data retention, no covert assessment operation. |
| Phone/queue orchestration | OpenClaw or optionally n8n around the chosen engine | One scheduler/ledger owner, secure review surface, no duplicate or bypass action paths. |

Cherry-picking is not blindly combining whole apps. Start with one source base and add only demonstrated gaps. Preserve source/license provenance and check actual reuse terms before copying. Adding three independent browser agents and two schedulers would increase collisions rather than solve missing behavior.

## First installation evaluation: LangHire, not an account-connected launch

Resolved default-branch snapshot: **e43d8faeaabe330a42697f02404580488d12088a**. Critical local-provider and application-worker files were re-fetched at this exact revision and matched the earlier reads. Some additional pinned re-fetches failed due connector transport errors; their findings rely on earlier successful default-branch reads. Recheck the exact checkout before modifying or running it.

Documented prerequisites: Node.js, Python **3.13+** from `pyproject.toml`, uv, Chromium/Playwright, and a reachable local model service. Rust is additionally needed for a source-built Tauri desktop package; the web/backend route avoids making a desktop build the first test. The inspected tree has npm/Cargo lockfiles but no uv lockfile, so Python dependencies must be resolved and captured for reproducibility rather than assumed fixed.

The concrete evaluation sequence is:

1. Download the pinned source into a separate evaluation directory under an isolated OS identity/VM with no personal browser session, mailbox, or full-vault access. Do not run a remote install script or public binary as the first security check.
2. Inspect install scripts and dependencies, capture resolved versions, and run its tests with synthetic data. Existing tests are not claimed passing here.
3. Configure native local inference explicitly. Disable app/upstream telemetry and external auxiliary/model paths; verify effective network behavior. Make the 32K context setting configurable and measure it on the host.
4. Remove automatic Gmail OTP access, account creation/reset, guessed personal answers, and unattended live submission. Add our explicit review/controller and an outcome-unknown state that prevents blind retries. Preserve narrow file access.
5. Add the one-page renderer validation and verified dossier references. Use one browser worker initially.
6. Test a synthetic local application page, missing personal answer, broken form, restart, timeout, and a one-page packet without real credentials. A dry-run against a live site can still disclose entered fields; it is not our first privacy test.
7. Only after those checks, review one real eligible role and explicitly authorize its exact live disclosure/submission. Keep prohibited platform actions and covert interview assistance outside this pilot.

This is a concrete candidate and adaptation checklist, not a completed installation or a promise the repo will pass. If required changes prove larger than its reusable value, use its components with our thin operator rather than force a wholesale adoption.

## Checkpoint

**Produced:** Source-backed project shortlist, model/privacy/license distinctions, concrete code findings, reuse map, and first-install evaluation sequence.

**Evidence:** GitHub repository metadata, READMEs, source trees, selected code/config/license/privacy files, and limited CI inspection. No local runtime test or employer/interview success validation.

**Recommendation:** Evaluate LangHire first as the specialized local application base; use ApplyPilot/AIHawk selectively as references. OpenClaw remains an optional coordinator rather than a reason to build everything afresh. Model choice is still open.

**Next / resume point:** Prepare the isolated pinned LangHire evaluation on the intended host, then test synthetic forms before account access. Keep this audit linked to the existing flow; no further broad opportunity or architecture planning is needed before that inspection.
