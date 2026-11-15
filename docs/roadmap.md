# Next increments

Progress: the standalone skill-match v1 validator and private per-validation reports are implemented; both saved model failures are rejected. This is one component of increment 1, not a completed workflow. See [output validation](output-validation.md).

1. **Validated synthetic workflow:** immutable run IDs/paths, deterministic schema
   and fact checks, explicit missing-answer review, bounded retries. Acceptance:
   the recorded omitted-skill response is rejected and retained, not promoted.
2. **Recovery control:** interrupted work needs an explicit resume decision;
   stale work cannot replace newer artifacts. Acceptance: kill/restart and restore
   cannot repeat an external action or revive an expired approval.
3. **Browser isolation:** build the supported Docker browser image, constrain
   networking, use a synthetic local form, and test injection/redirect/timeout
   behavior. Acceptance: no access to unrelated files, sessions or destinations.
4. **Dossier and one-page packet:** approved evidence, factual tailored text,
   deterministic PDF rendering, page count/readability/links and exact-packet review.
5. **Real permitted pilot:** only after the above, connect minimal accounts and
   review one exact application. Add social engagement recommendations and private
   phone review without handing the model unrestricted account sessions.

Model comparisons remain separate and deferred until their artifacts/runtime are
prepared. n8n, autostart and a multi-model controller are optional later choices,
not prerequisites to useful local drafting. These are planned increments, not
features already implemented by the published scripts.
