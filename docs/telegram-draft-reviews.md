# Telegram draft-review integration

Deployed through visible Cmux SSH on 16 November 2026, against installed OpenClaw
2026.11.3. This is an authenticated native command, not an LLM tool or a second
Telegram poller. It uses the existing owner-only private Telegram bot route.

## Use

Send these to the bot, one command per message:

    /careerreview help
    /careerreview new MY-TASK local,model,telegram,test,development
    /careerreview status REQUEST-UUID
    /careerreview approve REQUEST-UUID
    /careerreview reject REQUEST-UUID

Initial approved statement IDs are local, model, telegram, test and development.
They describe the current setup only. They are not a career dossier or permission
to make claims about privacy, model performance, completed job automation or skills.
A trusted human must approve any additional full statements before they enter the
private statement file. Neither Telegram command arguments nor the model can add facts.

The response contains the exact draft, task, revision, request UUID, digest, expiry
and decision commands. Approval records review only. Nothing is published or submitted.
Normal chat replies and bare APPROVE/REJECT messages do not update this store. Use
only /careerreview commands for durable state. A conversational reply alone is not
proof that a persistent operation occurred.

Repeating identical new TASK IDs and selections returns the existing latest revision
and does not extend expiry. Changed approved facts or selections create a new revision
and supersede prior pending/approved requests. Decisions are accepted once. Duplicate,
expired, stale, malformed, wrong-sender and non-private invocations fail closed.

## Installed separation

- Source plugin: extensions/career-review/ (manifest, package metadata, index.mjs).
- Deployed plugin: ~/career-ai/openclaw-plugins/career-review/.
- Trusted Python runtime snapshot: ~/career-ai/review-runtime/.
- Private settings, statement file and SQLite state: ~/career-ai/review-state/.
- Settings and state files use mode 0600; the state directory uses mode 0700.
- The database and Python runtime are outside agent workspaces. The notification
  agent still has no shell, filesystem, browser or publication tools.
- The plugin registers only careerreview. It launches a fixed Python module with
  fixed arguments and passes command data over stdin; no shell interpolation.
- The plugin checks Telegram channel, authenticated numeric sender, private From
  identity, default account and absence of thread/parent context. OpenClaw's existing
  owner allowlist and disabled groups remain unchanged. Python checks the owner again.
- Review content is transmitted through Telegram. Local model inference does not make
  Telegram messages local-only. Initial review statements contain no resume or secrets.

## Reproduce on an already configured host

First configure the existing private Telegram route with one numeric owner allowlisted,
groups disabled and a functional gateway. Do not add a new getUpdates poller. Keep
credentials out of this repository. Review the source before enabling native host code.

1. Copy the three files in extensions/career-review/ to the deployed plugin directory.
2. Create workflow/ and validation/ packages in the private runtime directory, each
   with an empty __init__.py. Copy workflow/draft_approval.py, workflow/telegram_review.py
   and validation/grounded_draft.py to the corresponding package directories.
3. Create the private state directory and an operator-approved approved-statements.json.
   The example file supplies only the initial setup statements; verify them for your host.
4. Write settings.json with owner (numeric ID string), database (absolute SQLite path)
   and facts (absolute approved-statements.json path). Set file permissions to 0600.
5. Preserve a private backup of openclaw.json. Append the deployed plugin directory to
   plugins.load.paths without removing existing entries. Enable plugins.entries.career-review
   and set config.owner, config.repo (runtime directory), config.python (absolute Python
   executable), and config.settingsFile. Preserve all channel, binding, tools and agent
   policies. Do not put owner-specific configuration or credentials in Git.
6. Run openclaw config validate. Only after it passes, restart the managed gateway.
   Confirm plugin inventory contains commands: [careerreview], not merely status: loaded.
7. Append config/telegram-review-guidance.md to the notification workspace instructions,
   preserving existing restrictions and a private backup.
8. Send a new test request through Telegram, verify its database row, reject it, and
   confirm the decision survives a gateway restart. Test approve and duplicate refusal.

The manifest must include its strict configSchema, activation.onStartup=true, and the
careerreview runtime-slash command alias. Without the schema, config validation rejects
plugin settings. Without activation metadata, the plugin can appear loaded while its
command is absent; a model may produce a misleading lookalike response. Both issues
were encountered during setup and corrected. The manifest regression test prevents
reintroducing the missing activation/ownership declaration.

## Verification and recovery

    python3 -m unittest discover -s tests -v
    node --test tests/test-career-review.mjs

Automated tests cover the real plugin-to-Python subprocess path, private-chat admission,
read/create/approve/reject, duplicate creation/decision, invalid commands, and manifest
activation. The broader store tests cover revision changes, expiry, snapshot consistency,
concurrency and separate-process recovery. See examples/results/telegram-review-tests.json.

To roll back, stop the gateway, restore the exact reviewed pre-change configuration
backup and prior notification instructions, validate config, then restart the gateway.
Retain the private state and backups for review. Do not delete review history or run
doctor --fix as a substitute for understanding a validation failure.

## Remaining scope

This does not trigger career jobs, scrape social feeds, generate arbitrary verified prose,
authorize publication, add new facts autonomously, or guarantee exactly-once Telegram
delivery. New-request retries are idempotent at the task/draft level; decision retries
are refused after the first transition. The sender metadata and poller deduplication
remain OpenClaw's transport responsibility. Host clock and OS integrity remain trusted.
