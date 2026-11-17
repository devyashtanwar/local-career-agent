# Read-only PC status over Telegram

The native /pcstatus command reports Linux host telemetry through fixed trusted code,
without an LLM or arbitrary shell execution. /pcstatus help explains the scope; every
other argument is refused. This extension is independent of the draft-review PR.

## Data and limits

- UTC sample timestamp, uptime in hours and one-minute CPU load (not CPU percentage).
- RAM used/total/available from MemTotal and MemAvailable in /proc/meminfo.
- Free/total space on the host home filesystem, in GiB; this is not every mounted disk.
- NVIDIA GPU name, VRAM used/total in MiB, utilization and temperature from a fixed query.
- Four named user-service states: OpenClaw, Traefik, local-model service and rootless Docker.

Missing tools, timeout, unsupported fields and malformed readings are unavailable or
unknown. An active model service does not establish that a model is loaded or ready.
No process listings, file contents, credentials, command-line arguments, journal records
or generic host logs are returned. No service restart, repairs or changes are supported.

The collector runs two allowlisted commands without a shell: /usr/bin/nvidia-smi and
/usr/bin/systemctl --user is-active for four exact units. Each has a three-second timeout;
the plugin bounds its child to ten seconds and 16 KiB output. These checks are read-only,
not an OS isolation boundary against an operator able to modify host code.

## Access and deployment

Source: operations/pc_status.py and extensions/pc-status/.
Deployed runtime snapshots: ~/career-ai/pc-status-runtime/ and
~/career-ai/openclaw-plugins/pc-status/. Updating the source checkout does not update
those runtime copies. File copies and configuration updates require operator review.

The native command is Telegram-only and requires OpenClaw's admitted sender plus the
plugin numeric-ID allowlist. It rejects groups, threads, unexpected accounts and extra
arguments. The current deployment reuses the existing owner-only channel policy; partner
onboarding remains separate pending a verified numeric Telegram identity and permissions.
No model tools or existing channel/agent policies were broadened.

To reproduce on an already configured OpenClaw host:

1. Create private runtime and plugin directories. Copy the operations package to the
   runtime and the three extension files to the plugin directory.
2. Back up openclaw.json privately. Append the plugin directory to plugins.load.paths.
   Enable plugins.entries.pc-status with config.allowedUsers (numeric strings), config.repo
   (absolute runtime path), and config.python (absolute Python executable). Match the
   existing Telegram allowlist; keep groups disabled and other policies intact.
3. Preserve the manifest's startup activation and native slash-command alias. Validate
   configuration before restarting the gateway. Restore the backup if validation fails.
4. Verify plugin inventory lists pcstatus, then test the real Telegram command and a
   rejected argument. Do not treat a model-generated lookalike reply as proof of routing.

## Verification

    python3 -m unittest discover -s tests -v
    python3 -m unittest discover -s inference -p 'test_*.py' -v
    node --test tests/test-pc-status.mjs

Collector tests cover actual query schema, unsupported readings, malformed/nonfinite
values, partial failures and timeout. The plugin test calls the real subprocess and
checks sender/channel/group/account/thread rejection and argument refusal. Manifest
activation is covered explicitly. No model inference is needed for this command.

See examples/results/pc-status-tests.json for recorded execution evidence. Live Telegram
confirmation is recorded separately from automated checks.

## Next work

Failure/recovery notifications, off-host PC availability detection, shared-participant
roles, note capture, agency workflows and model-lab queues remain planned. No recurring
monitor or automatic system repair was installed by this status increment.

Live verification on 16 November 2026: the user confirmed real Telegram readings and
refusal of /pcstatus restart. Deployed module/plugin bytes matched this source, and
the private runtime collector and active gateway were checked directly.
