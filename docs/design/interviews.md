> Proposed workflow, not a deployed feature or completed security assessment. See [current findings](../findings.md) for what the installed baseline actually did.

# Interviews and job decisions

Up: [Start here](../architecture.md).

## Response to better-job decision

```mermaid
flowchart TD
    A[Recruiter message you import or narrowly approved local read] --> B[Verify sender role and message authenticity]
    B --> C{Trusted and linked to known opportunity?}
    C -->|No E04 E28| C1[Quarantine or ask you to verify]
    C -->|Yes| D{Message type?}
    D -->|Rejection| R[Record actual outcome and reason only if given]
    D -->|No response| N[Retain no-response state and reasonable review date]
    D -->|Question| Q[Draft grounded answer for you to send]
    D -->|Interview| I[Compare timezone availability and existing commitments]
    I --> J{Conflict or unclear timezone?}
    J -->|Yes E29| J1[Ask you or draft alternative slots]
    J -->|No| K[You confirm scheduling]
    K --> L[Prepare using exact submitted packet and company evidence]
    L --> M[You attend and supply notes afterwards]
    D -->|Assessment| S[Identify rules effort deadline and identity requirements]
    S --> S1{Requires your own work or sensitive action?}
    S1 -->|Yes E30| S2[You complete it with preparation support only]
    S1 -->|Unclear| S3[Clarify requirements before proceeding]
    M --> T[Capture feedback without inventing the cause]
    S2 --> T
    R --> W[Weekly bottleneck review]
    N --> W
    T --> W
    D -->|Offer| O[Compare written terms with your better-job criteria]
    O --> O1{Missing terms or material concerns?}
    O1 -->|Yes E31| O2[Draft clarification or negotiation for you]
    O2 --> OW[Await actual reply while search follows your policy]
    OW -->|New written terms arrive| O
    O1 -->|No| O3{Your decision?}
    O3 -->|Accept| Z[Pause search and manage transition]
    O3 -->|Negotiate| O2
    O3 -->|Decline| OD[Record declined offer and continue search]
    OD --> W
    W --> Y[Adjust one search portfolio or interview bottleneck]
```

The assistant does not accept offers, sign terms, resign, impersonate you in interviews, or fabricate explanations for rejection. It may help prepare, compare options, and draft communication for your review. Legal and contractual uncertainties require appropriate human advice; the system cannot certify an offer.

## Better-job criteria

Agree your priorities before ranking offers: work type and interests, compensation structure, growth, team quality, manager expectations, location/remote restrictions, hours/timezone, stability, notice period, and personal constraints. A higher quoted number is not automatically a better offer; variable pay, equity uncertainty, contractor costs, probation, restrictive terms, and work-country eligibility may change the comparison. Use written evidence and explicit assumptions.

No-response, rejection, interview, offer, accepted, declined, and withdrawn are distinct states. Acceptance is your recorded decision, not an inference from an email. After acceptance, pause applications and visibility suggestions implying availability, cancel outstanding drafts, and let you decide how to notify other employers and your current employer. A later decision to restart is explicit.

## Weekly review

Look separately at discovery quality, packet correctness, your active minutes, meaningful conversations, interview conversion with an adequate observation window, and interview outcomes. Avoid simultaneous strategy changes that make learning impossible. A recurring skill gap may justify a portfolio increment; a broken submission workflow may justify manual applications. The system should stop expanding automation when maintenance exceeds the value it creates.
