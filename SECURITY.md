# Security and privacy

This is an experimental single-operator deployment, not a hardened multi-user
service. Do not use its current model/configuration for unattended personal-account
actions. There is no guarantee that local software cannot disclose data.

## Implemented configuration

- Local model endpoint with no cloud fallback; cloud memory search disabled.
- Gateway bound to loopback with a locally generated token; private config mode 600.
- All-session Docker tool sandbox; rootless daemon selected by guarded launchers.
- Tool root filesystem read-only, network disabled, capabilities dropped,
  no-new-privileges, 1 GiB memory limit and 128-process limit.
- Workspace-limited file tools. Shell, automation, messaging, spawned agents,
  plugin tools, unrestricted web and browser tools denied to the model.
- No account credentials or normal browser profile imported.
- Chromium sandbox kept enabled for the operator-only public-page trial.
- Telemetry/diagnostic export/update checks/cron/hooks disabled in the template.

Namespace UID 0 maps to the ordinary host user under rootless Docker, rather than
host root. It is needed for mounted workspace ownership in this configuration.
Never point this template at a rootful Docker daemon. The launchers check for
rootless mode, but direct invocation of binaries can bypass launcher checks; the
human operator still controls that authority.

## Limits

The gateway and inference server run on the host, outside tool containers. No
OS-wide outbound firewall, dedicated host OS account, encrypted backup system or
browser egress broker was established by the recorded pilot. Localhost binding
limits incoming connections, not outgoing traffic or access by local software.
The model API currently has no enforced authentication. A generic OpenAI key is
only a compatibility placeholder.

Downloads and browser requests contact external services. Gateway startup logged
a remote model-catalog update despite the chosen settings. Local inference does
not mean that every process is offline. Verify traffic and auxiliary providers
before introducing private data. Social and employer sites necessarily receive
the material deliberately disclosed to them.

Prompt rules are not permission controls. A small model made factual mistakes,
and an interrupted task resumed and replaced a prior output. A zero-critical
audit report is not evidence of universal correctness, confidentiality or safe
retries. The remaining reverse-proxy warning is acceptable only while no proxy
exposure is configured; do not add broad trusted proxy ranges to silence it.

## Before account integrations

Implement deterministic schema/fact checks, immutable per-run artifacts,
idempotent action records, exact-payload approval, destination restrictions,
unknown-outcome reconciliation and revocable authorization. Test restart, outage,
expired approval and malicious page behavior. Configure and test a separate
browser sandbox/network policy; the public operator browser test did not prove it.
Use human login/MFA in a dedicated profile only when an integration has passed
review. Never mount home directories, SSH keys, mailbox credentials, password
stores, a full notes vault or the container socket into the worker.

## Repository hygiene

Keep generated config, tokens, cookies, resumes, emails, real application records,
browser state, model weights and raw logs out of Git. Ignore rules are a convenience,
not a secret scanner. Review every staged file and previous commits before pushing.
If credentials are exposed, revoke/rotate them; deleting a tracked file does not
remove it from Git history or copies already downloaded.

Report a security issue privately through GitHub's private vulnerability reporting
feature if the owner enables it. If unavailable, use a minimal public issue asking
for a private reporting route; do not include credentials, private logs, exploit
payloads against third parties or personal application data.
