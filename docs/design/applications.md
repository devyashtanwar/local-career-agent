> Proposed workflow, not a deployed feature or completed security assessment. See [current findings](../findings.md) for what the installed baseline actually did.

# Opportunities and applications

Up: [Start here](../architecture.md). Exceptions: [E01–E40 handling](exceptions.md).

## Discovery and qualification

```mermaid
flowchart TD
    A[Scheduled run or you import a lead] --> B{Source access permitted?}
    B -->|No E01| B1[Use manual import or permitted alternative]
    B1 --> C
    B -->|Yes| C[Fetch only necessary public job data]
    C --> D{Source available?}
    D -->|No E02 E03| D1[Honor rate limit or bounded backoff then source pause]
    D1 --> A
    D -->|Yes| E[Resolve employer and actual application destination]
    E --> F{Authentic destination verified?}
    F -->|No E04 E05| F1[Quarantine scam or unresolved link for review]
    F -->|Yes| G{Current and not withdrawn?}
    G -->|No E06| G1[Archive as closed or stale]
    G -->|Yes| H{Same role already tracked or applied?}
    H -->|Yes E07| H1[Merge source evidence without another submission]
    H -->|No| I{Excluded employer or prior status conflict?}
    I -->|Yes E08| I1[Skip or ask about explicit exception]
    I -->|No| J[Apply hard constraints and evidence based fit]
    J --> K{Critical eligibility known?}
    K -->|No E09 E10| K1[Ask precise question or seek source evidence]
    K1 -->|Answer verified| J
    K -->|Yes| L{Suitable now?}
    L -->|No E11| L1[Reject with reason or queue a useful skill gap]
    L -->|Yes| M[Prioritize by fit timing and your attention budget]
    M --> N[Prepare application packet]
```

Remote does not automatically mean worldwide. Distinguish work country, timezone, employment type, sponsorship, relocation, and required attendance. Normalize salary currency, annual/monthly basis, gross/net ambiguity, fixed/variable components, and missing ranges before comparing. Unknown compensation need not reject a role if your policy allows review; do not invent a range.

Deduplicate using employer/requisition identity plus canonical posting, not just title. A referral arriving after application updates the existing record; ask about the employer's referral process rather than submitting again. Different roles at one employer may be distinct but still trigger an employer-level application policy.

## Prepare, review, submit, confirm

```mermaid
flowchart TD
    A[Qualified role] --> B[Select approved evidence and render tailored resume]
    B --> C{Claims and document checks pass?}
    C -->|No E12 E13| C1[Repair or ask for evidence then regenerate version]
    C1 --> B
    C -->|Yes| D[Read required questions in permitted form]
    D --> E{Unsupported form or automation restricted?}
    E -->|Yes E01 E14| E1[Prepare packet and hand form to you]
    E -->|No| F{Login MFA or CAPTCHA required?}
    F -->|Yes E15| F1[You authenticate or take over the form]
    F1 --> F2{What happened?}
    F2 -->|Authentication only| G
    F2 -->|You completed it manually| U
    F2 -->|Cancelled or unfinished| J1
    F -->|No| G[Map verified answers without guessing]
    G --> H{Unknown sensitive or consequential answer?}
    H -->|Yes E16 E17| H1[Save ticket and wait for your exact answer]
    H1 -->|Answer scoped and current| G
    H -->|No| I[Show employer domain files fields and consent choices]
    I --> J{You approve this exact packet?}
    J -->|No or silence E18| J1[Hold revise or cancel without sending]
    J1 -->|Revised| B
    J -->|Yes| K[Lock item and recheck packet policy deadline destination]
    K --> L{Still valid and unchanged?}
    L -->|No E19 E20| I
    L -->|Yes| M[Controlled adapter sends once with durable attempt record]
    M --> N{Submission result?}
    N -->|Explicit validation failure E21| G
    N -->|Confirmation| O[Store confirmed submission and evidence]
    N -->|Timeout or ambiguous E22| P[Outcome unknown stop retry and reconcile]
    P -->|Receipt or portal proof| O
    P -->|Not provably resolved| P1[Manual review before any retry]
    E1 --> U[You report manual result with evidence]
    U --> U1{Receipt evidence available?}
    U1 -->|Yes| O
    U1 -->|No| U2[Record user reported or outcome unknown without resubmitting]
```

Manual completion does not become confirmed simply because you opened the form. If you cannot provide evidence, record user-reported submission or outcome-unknown separately from machine-confirmed submission.

Approval must bind job ID, employer/destination, packet version/hash, file contents, outgoing fields, action, and expiry. If any changes, ask again. A browser may transmit typed fields before its Submit button is clicked; stage personal answers locally and approve disclosure before the controlled worker fills the live form. Preview uploads, pre-submit autosaves, and application tracking scripts are part of the approved destination's data exposure.

The model cannot hold unrestricted browser/shell/network access that bypasses this controller. A domain allowlist alone cannot prevent leaking data to an unintended recipient at an allowed site. The controller validates action, role, form endpoint, recipient, payload, redirects, and permitted attachments too. Employer third-party hosts must be included in the review; a changed host stops the action.

Use durable attempts, a local uniqueness constraint/lock, and receipt reconciliation. These reduce duplicates but cannot guarantee exactly-once submission on a website without server-side idempotency. Never silently retry a timed-out external write. Explicit field-validation errors allow repair, but changes still invalidate the old packet approval.

## Follow-up and progression

After confirmed submission, keep the packet and receipt, review selected recruiter messages locally, and set a reasonable review date. Draft a relevant follow-up for you if useful; do not auto-send repeated outreach. No response remains no-response until evidence changes it. See [interview and offer flow](interviews.md).

A future auto-submit policy is not active in this design. It would need explicit authorization for a narrow employer/source set, approved facts and consent rules, tested adapters, caps, and exception handling. Identity documents, legal declarations, unfamiliar terms, assessments, or failed checks still require you.
