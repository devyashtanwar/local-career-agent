# Local model worker — verified synthetic pilot

On 15 November 2026, the installed OpenClaw 2026.11.3 embedded runner and Qwen3.5-9B Q4_K_M through LM Studio completed the controller-managed skill-match task on the Omarchy PC. This is integration evidence for one narrow task, not a model benchmark or a production-readiness claim.

## What the operator runs

Use the existing installation guide to prepare LM Studio and the rootless Docker sandbox. Keep Docker in a visible foreground terminal. Keep the OpenClaw gateway stopped: this adapter uses embedded mode and a fresh native session for each attempt. Load the registered qwen3.5-9b model with identifier career-qwen35-9b, context 16384, parallelism 1, and expose LM Studio on 127.0.0.1:1234 only.

Create trusted candidate/requirements JSON outside the agent workspace using the schema in output-validation.md. Create a run with the existing controller; copy its run_id. From the repository checkout, invoke:

    python3 -m workflow.openclaw_worker RUN_ID --timeout 180

Defaults: state root ~/career-ai/workflow-state; workspace ~/career-ai/workspace; executable ~/career-ai/openclaw/openclaw.sh; configuration ~/.openclaw/openclaw.json. Explicit --state-root and --workspace must refer to the same ledger/workspace used to create the run. Exit 0 means validated or review_required; exit 2 means refused, rejected, interrupted, or superseded. It never authorizes an external action.

## Dispatch and result handling

The operator-installed executable must be outside the model workspace. Before claiming a run, the adapter compares the private configuration against config/openclaw.template.json rendered for the operator home. Only metadata and the nonempty private gateway-token value may differ. Cloud providers/fallbacks, tools, workspace or sandbox drift is refused. A mode-600 temporary configuration snapshot is passed using the installed OPENCLAW_CONFIG_PATH resolver; OPENCLAW_STATE_DIR remains the original configuration parent. The snapshot is removed at exit. Do not publish that snapshot or native session logs.

The child receives an allowlisted environment, excluding inherited cloud credentials, proxies, SSH agent, NODE_OPTIONS and arbitrary OpenClaw overrides. Rootless-Docker enforcement remains the installed launcher's responsibility. A configuration-directory lock serializes adapters sharing that configuration; a ledger lock also prevents concurrent dispatch in one ledger. Direct native CLI/gateway launches can bypass these advisory locks, so operators must not run them concurrently.

After claim, the child gets only relative request/output paths and fixed task instructions. Request contents are untrusted data. A unique session ID includes both run and attempt IDs. Native stdout/stderr remain visible but never decide acceptance. Only the assigned result file, private trusted-input snapshots, deterministic validator and current-generation/attempt check decide the outcome.

A timeout, launch failure, nonzero exit or handled interruption stops the owned process group before recording interrupted. Even a valid file from a failed child is not accepted. There is no automatic retry. Explicit controller recovery creates a new attempt path and native session. Missing/malformed/wrong output is retained or reported as rejected. A superseded attempt cannot become the current result.

## Evidence

- 48 configuration/validation/controller/worker tests plus 13 inference tests passed: 61 total, including 11 new real-subprocess worker tests.
- Initial live task: review_required, no validation errors, about 23.77 seconds end to end. React.js and Python matched; SQL missing; work_authorization remained null; needs_review remained true.
- A second live run was intentionally stopped with a two-second adapter timeout. Completion was refused while interrupted. The operator test explicitly resumed it into a fresh attempt; the real model output again reached review_required. The old attempt was refused afterward. Total interruption-plus-recovery experiment: about 24.69 seconds.
- The recovered native execution trace identified career-local/career-qwen35-9b, embedded runner and no fallback. It recorded one failed tool call before recovering and producing correct final output. Two completed examples do not establish a reliability rate.
- Public summary: examples/results/model-worker-checkpoint.json. Private ledger/result snapshots and native traces remain outside the repository.

## Limits and recovery

This adapter does not change native OpenClaw recovery. SIGKILL, power loss or an OS crash may prevent cleanup, leaving a running ledger record and possibly native work. Inspect and stop surviving work before using controller interrupt/recover commands. Do not automatically infer that an old worker stopped from a lost SSH connection. Process-group cleanup cannot undo a tool write or cancel computation already accepted by the independent model server; fencing prevents an old attempt from being promoted through this controller.

The model tool sandbox has the configured workspace mount; this is not per-run filesystem isolation or a host-wide outbound firewall. The host-side OpenClaw process still runs as the operator. The locks and configuration comparison assume trusted operator-controlled code, templates and directories. Do not connect private accounts until browser, host-data, network and authentication boundaries are tested. No application, message or social action was performed.

Next increment: synthetic browser/form isolation and destination tests. Keep real credentials and browser sessions disconnected.
