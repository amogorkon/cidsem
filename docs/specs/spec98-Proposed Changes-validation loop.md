Overview (one-line)

Real-time symbolic extraction handles low-latency needs; dreaming (batch LLM + coref) produces curated triples. The Validation Layer sits between the micro-LLM fallback and CIDStore, surfacing low-confidence candidate factoids to humans (or community bots) for fast, auditable confirmation — preventing noisy LLM output from polluting the graph and producing labeled training data.

flowchart LR
  A[Raw Messages] --> B[Preprocessor/Chunker]
  B --> C[Symbolic Extractor (real-time)]
  C -->|high-confidence| D[Real-time Triple Insert -> CIDStore]
  C -->|low-confidence| E[Micro-LLM Guesser]
  E -->|confident| F[CandidateFactoid (pending)]
  F --> G[Validation Layer: Bot Prompt / Human Response]
  G -->|confirmed| D
  G -->|rejected| H[Backlog for Dreaming]
  H --> I[Dreaming Batch (LLM + Coref + Tripleizer)]
  I --> D
  I --> J[Predicate Registry / Migration & Training Data]

1. Where Validation Fits

Real-time path: Symbolic-only → immediate triple insert (no validation).

Micro-LLM fallback (real-time): Generates candidate factoids for ambiguous cases → these candidates MUST NOT be auto-inserted. They become CandidateFactoid records and are routed to the Validation Layer.

Validation Layer: converts candidate factoids into user/community prompts (via Barkeep, Critic, Historian), collects responses (ValidationEvent), and then either (a) upgrades the factoid to an asserted triple in CIDStore, (b) rejects and routes the candidate to Dreaming, or (c) expires to backlog.

2. Data Model (summary)
CandidateFactoid

factoid_cid (CID) — content-address of canonical candidate sentence

subject_cid / subject_raw

predicate_candidate_uri (+score)

object_cid / object_raw

confidence (float initial from micro-LLM)

provenance: { msg_cid, chunk_id, extractor_ver, prompt_hash }

status: pending_validation | confirmed | rejected | expired

created_ts, expires_at, priority

ValidationEvent

event_cid

factoid_cid

responder_id (user or moderator or system)

response: confirmed | rejected | abstain

timestamp, bot_id (if the prompt came from a bot), context_msg_cid (the chat message where prompt posted)

Backlog / Dreaming Item (if rejected or expired)

links to factoid_cid, validation_history, priority, and reprocessing metadata

3. Bot Behavior & UX Patterns
Barkeep (default)

Tone: friendly, minimal friction.

When used: candidate factoids where the original author can be pinged.

Example prompt: “Hey @Alice — quick check: Did you join the Chess Club? (Yes / No / Not sure)”

Critic (contradiction checks)

Tone: skeptical, precise.

When used: candidate factoids that contradict known high-confidence triples.

Example prompt: “We have a claim that Alice joined Chess Club in 2024, but records show otherwise. Is the claim correct?”

Historian (community confirmation)

Tone: contextual, community-oriented.

When used: broad claims or events where multiple confirmations are useful.

Example: “Community: did Alice join the Chess Club in 2024? Reply to confirm or cite evidence.”

Prompting rules

Only surface high-value/novel/ambiguous factoids. Rate-limit prompts per user and per channel to avoid spam.

Attach minimal context: source sentence, message link (msg_cid), one-line LLM justification (why it guessed).

Include 1-click responses (Yes / No / Not sure) and an optional “More info” button opening the Curation Console.

4. Validation Rules & Decisioning

Priority & routing:

critical factoids (security/moderation, user safety) auto-prioritized to human moderator lane with short TTL (e.g., 5–30 min).

high (high karma or admin flagged): short TTL (e.g., 1–4 hours).

normal/low: batched digest or TTL (24–72 hours).

Resolution algorithm:

If author confirms → mark confirmed, set confidence=0.95, insert triple with provenance validated_by: actor_cid.

If author rejects → mark rejected, drop candidate and route to Dreaming for deeper analysis.

If community responses:

≥2 distinct confirmed votes → confirm (unless author explicitly rejected).

≥2 distinct rejected votes or explicit moderator reject → reject.

If TTL expires with insufficient votes → mark expired and push to Dreaming backlog.

Conflict handling:

If author confirms but community rejects → set triple modality=belief with provenance showing both signals. Flag for moderator review.

5. Integration APIs (summary)
POST /candidate_factoids

Producer: micro-LLM fallback

Body: CandidateFactoid

Response: 201 { factoid_cid }

Side-effect: Enqueue validation action if priority rules apply.

GET /validation_prompt/{factoid_cid}

Returns prompt text and payload for bot to post.

POST /validation_event

Body: ValidationEvent

Side-effects: update CandidateFactoid.status; if confirmed → call CIDStore insert API; if rejected → route to backlog.

GET /backlog/claim

Dreaming workers pop rejected/expired items for reprocessing.

All events must include prompt_hash, model_version, and msg_cid to ensure auditability.

6. Provenance & Auditability

Every validation step is recorded in CIDStore as meta-triples:

(factoidCID, extractedBy, microLLM:vX/promptHash)

(factoidCID, validatedBy, userCID)

(factoidCID, validationEventCID, eventCID)

The inserted triple records assertedFrom referencing the factoidCID and the validationEventCID.

Full chain is walkable: triple -> factoid -> message -> validation events -> responders.

7. Karma, Incentives & Data Labeling

Confirmations and rejections are small reward events:

Author confirmation: small karma to author only if they affirm another’s claim (optional).

Confirmers earn small karma for useful validations; rejectors earn more if their rejection prevents a low-confidence hallucination from becoming asserted (weighted by downstream impact).

All validation events are stored as labeled examples: (text chunk, candidate factoid, validated_label) and fed to model retraining pipelines (Dreaming ops).

8. Metrics & SLAs to monitor

Validation throughput: prompts posted / responses received per hour.

Resolution latency: median time from prompt → resolution (target depends on priority).

Validation yield: % of candidate factoids confirmed vs rejected vs expired.

False positive reduction: number of candidate factoids prevented from auto-insertion.

Label generation rate: labeled examples per 1k messages.

User fatigue signals: average prompts per active user per day, opt-out rate.

Alerts:

TTL breaches (critical factoid unresolved past SLA)

High expired rate (many prompts not answered) → adjust routing/priority

Prompt spam incidents → tighten rate limits

9. Edge Cases & Safeguards

Noisy/hostile validation: allow moderator override + require moderator confirmation for high-impact triples.

User opt-out: users can opt out of being pinged; their messages still generate backlog items for Dreaming but not public prompts.

Privacy: don't expose PII in prompts; if a factoid contains sensitive PII, route directly to moderator lane (no public prompt).

Gaming / Sybil attacks: validation weight should consider rater reputation and stake; low-rep raters have less weight or are excluded for critical decisions.

10. Training & Feedback Loop

Confirmed/rejected events feed:

micro-LLM fine-tuning (supervised) — increases hypothesis quality for future cases.

confidence recalibration for combiner weights (symbolic vs LLM).

predicate registry suggestions (if recurring novel predicates appear in validated confirmations).

Periodic tasks:

Weekly retraining on accumulated labeled set.

Shadow testing: sample earlier real-time symbolic outputs and compare against the validation-augmented dreaming results to detect drift.

11. Implementation checklist (concrete steps)

Extend CandidateFactoid & ValidationEvent schema in CIDStore (or a parallel DB) with WAL logging.

Implement micro-LLM fallback hook to POST candidate factoids to /candidate_factoids.

Implement Bot Service(s) capable of:

fetching prompts (GET /validation_prompt/{factoid_cid})

posting into chat with one-click responses

receiving responses and POSTing /validation_event

Implement Validation Worker:

enforces rate limits, TTLs, weighting, consensus rules

calls CIDStore insert on confirmation

routes rejects/expired to Dreaming backlog

Hook validation events into karma system & labeled-data store.

Add monitoring dashboards and alerting for validation SLAs, prompt rates, and user opt-out rates.

Start with a small pilot: enable validation loop for 1–2 high-value predicates (e.g., t:joined, t:worksAt) and a soft rollout to a subset of users.

12. UX & Product Considerations

Keep prompts minimally invasive: single-sentence, one-click response, optional link to more context.

Support digest mode for moderators: daily list of pending validations to approve in bulk.

Provide a Curation Console view that shows:

Candidate factoid + LLM explanation

Validation history and votes

Quick buttons: Confirm / Reject / Send to Dreaming / Request Evidence

Expose "why we asked" in the prompt (e.g., "We detected the phrase 'I joined' — is this true?").

13. Example end-to-end (concrete)

Micro-LLM posts candidate:

{
  "factoid_cid":"f:0x123",
  "subject_raw":"Alice",
  "predicate_candidate":"t:joined",
  "object_raw":"Chess Club",
  "confidence":0.36,
  "provenance":{"msg_cid":"m:0x998","extractor":"microllm:v0.1"}
}


Bot prompts: “@Alice — did you join the Chess Club?”

Alice clicks Yes → client POST /validation_event { factoid_cid:f:0x123, responder: user:alice, response:confirmed }

Validation Worker sets confidence=0.95, serializes canonical triple, computes triple CID, writes triple + provenance into CIDStore.

The event is logged; the labeled example is appended to the training corpus.