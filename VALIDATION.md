# Validation checkpoint — 15 November 2026

## Publication-time local checks

- Original inference suite: **13 tests passed** on the publication Mac. The first
  restricted run could not bind its local HTTP fixture; rerun with temporary
  localhost access passed all 13. No external account/API was contacted.
- New portable configuration suite: **3 tests passed**. Tests verify local path/
  private-token generation, restrictive config permissions, refusal to overwrite
  existing configuration and rejection of a symlinked state directory.
- Configuration tests were run before implementation and failed for the missing
  renderer, then passed after it was added.
- Shell scripts checked with `bash -n`; config/model/example JSON parsed locally.
- Relative documentation and Canvas targets checked for existing files.
- Public files checked for known home paths, SSH details, private addresses,
  credential patterns and excluded raw private artifacts; exported config uses
  only a token marker. This is a targeted review, not proof of no possible secret.

## Separate hardware evidence

The staged original setup ran on one RTX 3060 / Omarchy host. It established API
and tool connectivity, a constrained sandbox, a boundary check, audit findings
and clean shutdown. It also produced a factual-answer failure and unsafe shared
output behavior on automatic recovery. See [findings](docs/findings.md) and the
selected synthetic results. Passing packaging tests do not erase those failures.

## Not tested here

A full clean-host install of the published wrappers, different distro/GPU/Node
versions, sandboxed browser control/networking, private-data egress isolation,
cloud-free operation of every upstream component, real accounts, application
submission, social publication, PDF production, model comparisons and a durable
approval/recovery controller. No production-readiness or hiring outcome claim.

## Output-validation increment — 15 November 2026

All work executed visibly through Cmux SSH on the original Omarchy PC. 17 new validator tests plus 3 configuration and 13 inference tests passed (33 total). Actual saved omission/recovery results were rejected; a handwritten correct fixture was accepted with human review still required. Original input files and exact retained output hashes were verified. No model/account/browser/service was started. This does not establish automatic recovery safety or arbitrary resume factuality. See docs/output-validation.md and examples/results/output-validation-checkpoint.json.

## Run-control increment — 15 November 2026

17 new recovery/controller tests passed; total suite: 37 config/validator/controller tests plus 13 inference tests (50). Separate CLI processes demonstrated fenced old runs, duplicate-completion rejection, preserved result snapshots, explicit resume/cancel and actual saved-failure rejection. Process-death and transaction-rollback tests passed. All work ran visibly through Cmux with synthetic data; no model/browser/accounts started. Native OpenClaw recovery is not disabled, and a model-driven controller adapter is not yet integrated. See docs/run-recovery.md.

## Local-model worker increment — 15 November 2026

61 tests passed (48 main + 13 inference, including 11 new subprocess-worker tests). Two completed real-model skill-match tasks reached review_required, with an intentional two-second interruption and explicit fresh-attempt recovery between them; stale completion was refused. One native tool error recovered before correct output. This verifies a narrow integration, not autonomous account use or a general reliability rate. See docs/model-worker.md and examples/results/model-worker-checkpoint.json.
