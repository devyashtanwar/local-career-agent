# Grounded draft reviews: initial offline increment

Implemented on Omarchy through visible Cmux SSH, 16 November 2026.

## Evidence and decision

The user supplied screenshots of a conversational test: rejection stopped a draft;
approval produced a draft. Even with explicit constraints, the model added a privacy
claim and generalized a conversational test to the whole workflow. Relevant excerpts
are manually transcribed in examples/grounding-regressions.json. These are regression
inputs, not a complete transcript or evidence that anything was published.

We therefore do not accept model-generated prose as verified text. This increment
uses a deliberately restricted renderer: a trusted operator approves whole statements
under stable IDs, and a model may select IDs only. Output is assembled from the exact
approved statements, separated by paragraphs, with a 120-word limit. Unknown IDs,
free prose, duplicates, malformed inputs and overlong drafts are rejected.

This is a construction constraint, not a general semantic fact checker. A model cannot
approve its own facts. Incorrect, outdated or misleading operator-approved statements
remain possible. Selection and omission can still mislead; human review remains required.
Free-form model drafts remain unvalidated and must not enter this approval path.

## Persistent review contract

workflow.draft_approval.ApprovalStore uses a private SQLite file outside the agent's
workspace. Use a dedicated directory, for example ~/career-ai/review-state/, mode 0700,
and a database mode 0600. No production database or Telegram route was enabled here.

create(task, facts, selection, ttl=3600) snapshots approved statements, selection and
rendered draft, with a SHA-256 digest, random request UUID and increasing task generation.
Expiry must be 1–86400 seconds. A changed revision supersedes earlier pending or approved
requests. Recreating the identical latest revision is refused; this does not renew expiry.

A trusted transport must display the exact stored draft, task, generation, request UUID,
digest and expiry to the user. It must derive actor from authenticated Telegram sender
metadata, not text or an LLM. Bind the route to the authorized private chat. Call
store.decide_message(actor, 'APPROVE <request UUID>') or the exact REJECT equivalent.
Whitespace additions, extra instructions and ambiguous replies are refused.

Only pending current requests can be decided. Wrong senders, unknown/stale IDs,
duplicates, malformed replies, payload/digest mismatch and backward clock movement fail
closed. Expired requests are persisted as expired. SQLite transactions serialize competing
replies; reopening the store preserves requests and owner binding. Expiry is checked on
decision; there is no background expiration worker. now is a test seam for trusted host
code only, never an input supplied by the model or message sender.

Approval only records draft review. action_authorized is always false. No publisher,
application submitter, process runner, browser access or Telegram poller is included.
No new tools or permissions were granted to the notification agent.

Hashes catch accidental mismatches; they are not authentication against a user or
process able to rewrite both the database and digest. Keep this database inaccessible
to agent tools. OS compromise, clock integrity, source factuality, database encryption,
and transport delivery guarantees are outside this increment.

## Verification

Run from repository root:

    python3 -m unittest discover -s tests -p test_grounded_approval.py -v
    python3 -m unittest discover -s tests -v

Tests use temporary databases, synthetic owner IDs and no network/model/credentials.
They cover screenshot regressions, allowed rendering, malformed data, length, exact
reply parsing, rejection, expiry, duplicate and concurrent replies, stale revisions,
immutable snapshots, changed payloads, restart/reopen behavior and private permissions.

## Next integration increment

Connect a trusted host adapter to the existing owner-only Telegram route without giving
the LLM access to the database. Inspect OpenClaw's installed extension hooks first;
do not introduce a second getUpdates consumer or bypass notification-agent isolation.
Test the exact displayed draft against the stored digest, Telegram update replay,
private-chat identity, duplicate delivery, changed drafts and a real service restart.
Until then the live Telegram bot still runs its existing conversational behavior.

## Telegram integration update

The native command integration is now deployed. See [Telegram draft reviews](telegram-draft-reviews.md) for the verified scope and operational commands. The original offline verification above remains historical evidence.
