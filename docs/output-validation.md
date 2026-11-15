# Output validation: skill-match v1

Implemented and tested on the Omarchy PC on 15 November 2026, through visible
Cmux SSH only. This is a deterministic host-side validator, not another LLM.
It makes no network/model calls and never authorizes account actions.

## Contract and scope

Trusted candidate facts must contain skills (string array) and work_authorization
(null or a nonempty exact answer string). Other profile fields are ignored.
Trusted role requirements must contain required_skills (nonempty string array).
The caller is responsible for approving and grounding those inputs; this module
cannot determine whether a person's dossier or a parsed job description is true.

The model result must have exactly these four fields:

- matching_skills: all required skills present in the trusted candidate facts.
- missing_skills: all required skills absent from those facts.
- work_authorization: the exact trusted value, including null when unknown.
- needs_review: a strict Boolean, true exactly when that authorization is unknown.

Required skills must be partitioned completely, without additions or duplicates.
Comparison trims outer whitespace, ignores case and applies only two reviewed
aliases: React.js and ReactJS map to React. Order is irrelevant. There is no fuzzy
or substring matching: React Native is distinct from React; C is distinct from C++.

JSON must be bare UTF-8 JSON. Duplicate object keys, NaN/Infinity, numeric overflow,
trailing text and fenced responses are rejected rather than silently repaired.
Missing/extra fields, wrong types and inconsistent review flags fail validation.

A valid result can still require human review. Conversely, requires_review=false
only means this specific authorization field is known and validation passed.
It does not mean the candidate qualifies, a resume is approved, all declarations
are answered, or an application may be submitted. action_authorized is always false.

This is not a free-form resume factuality checker, ATS score, legal eligibility
determination or complete production validation framework.

## Run from the repository root

The included inputs and correct result are handwritten synthetic fixtures:

    python3 -m validation.skill_match \
      --candidate examples/candidate.synthetic.json \
      --requirements examples/requirements.synthetic.json \
      --output examples/results/skill-match-correct.synthetic.json

To replay the recorded factual failure, change --output to:

    examples/results/final-gateway-output-failed-validation.json

For the malformed result produced by interrupted-session recovery, use:

    examples/results/restart-recovery-overwrite.json

Exit codes: 0 = result validated; 2 = rejected input/result with retained report;
1 = validation unavailable because evidence could not safely be persisted.
A caller must stop on every nonzero exit, and must inspect requires_review even
on exit 0. Printing valid JSON or completing a model tool call is not a pass.

No existing OpenClaw command is automatically intercepted. Future workflow
consumers must call this gate before promoting an output, and a separate approval
controller must handle all outbound actions. Do not let the model's own claim
of successful validation substitute for calling the trusted validator.

## Evidence and trust boundary

Each invocation creates a new timestamp-plus-random-ID folder under
~/career-ai/validation-runs, outside the default agent workspace. It stores:

- report.json: version, decision, stable error codes, expected fields and SHA-256
  bindings for the exact readable input bytes used.
- model-output.bin: exact bounded model output bytes, including malformed JSON.

Candidate/job files are hashed rather than copied. Reports and raw output can
still contain private information; keep them local and out of Git/notes sync.
Directories are mode 700 and files mode 600; files use exclusive creation.
Input files are never rewritten. Repeated validations produce separate evidence,
not a replacement report. Inputs are capped at 64 KiB and must be regular files;
final-component symlinks and special files are rejected. Oversize/unreadable
outputs produce rejection metadata rather than an unbounded retained payload.

Candidate/requirements inside the default agent-writable workspace are rejected.
The report root must also remain outside it. This guard matches the published
~/career-ai/workspace configuration; do not change that deployment path without
updating the validator's configured boundary. This is tool-policy separation,
not a separate OS user: a compromised host gateway with the same OS identity may
still access these files. No complete outbound or host isolation claim is made.

Per-validation evidence does not solve the earlier agent's automatic recovery:
agent output files can still be replaced before validation, and valid but stale
results still need run/payload approval binding. Workflow-level immutable outputs,
explicit resume decisions, action idempotency and crash durability remain next.
Never poll a shared mutable output file as though it were an approved submission.

## Verified results

- 17 new validation tests passed; 3 existing config tests and 13 inference tests
  also passed (33 total). No model, gateway, browser, credentials or accounts started.
- The actual saved omission returned exit 2 with output.missing_skills_mismatch.
- The saved recovery result returned exit 2 with output.schema_fields.
- A correct handwritten result returned exit 0 and requires_review=true.
- Exact original files stayed unchanged; retained output hashes matched.
- Tests cover invented skills/authorization, strict types, aliases, malformed and
  nonfinite JSON, trusted-input boundaries, private per-run evidence, CLI exit
  behavior and inability to persist a report.

The first tests failed before implementation. Additional tests exposed numeric
float overflow and model-writable trusted-input gaps; both were fixed and retested.
This is offline regression evidence, not new model-quality or browser testing.
See examples/results/output-validation-checkpoint.json for sanitized CLI decisions.

## Run-control follow-up

The host-side controller now adds private input/result snapshots, unique attempt paths and explicit recovery. See [run isolation](run-recovery.md). Model-driven integration, native OpenClaw recovery behavior and account-action approval remain separate.
