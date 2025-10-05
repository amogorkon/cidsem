```markdown# 8. Query & Reasoning Layer

# Error handling, logging, and auditability

Built on top of the CIDStore and WAL-backed write-ahead logging.

Principles
- Immutable audit trail: every state transition (candidate created, prompt emitted, validation event received, triple insert) is recorded in WAL and, where appropriate, expressed as meta-triples in CIDStore that reference CIDs.
- Idempotency: side-effects (enqueue, insert_triples) MUST be safe to retry. Clients MAY provide `Idempotency-Key` headers for POST endpoints; services MUST consult WAL to deduplicate.
- Fail-fast for invalid inference outputs: inference outputs failing JSON Schema validation are assigned `confidence=0` and routed to a low-priority backlog or dead-letter queue for human review.

WAL and idempotent inserts
- All writes to CIDStore must be WAL-backed. A WAL record contains: request metadata (`request_id`, `Idempotency-Key`), payload (CandidateFactoid/TripleRecord), provenance references (`factoid_cid`, `event_id`), and timestamp (`inserted_at`).
- `POST /cidstore/insert_triples` MUST write WAL before attempting physical insert. The WAL enables idempotent retries: when a duplicate write is detected (same `Idempotency-Key` and payload), the service should return the prior result.
- Insert endpoint returns per-triple result with `triple_cid` (32-hex) on success or an error object `{code, message, details}` per failed triple.

Retries & dead-lettering
- Backlog/Dreaming job failures: retry with exponential backoff; after a configurable number of attempts move to a dead-letter queue for human review.
- ValidationEvent processing failures: record event in WAL, mark `CandidateFactoid.status = "confirm_pending"` and schedule a retry; escalate if pending beyond SLA.

Auditability & provenance
- Record meta-triples linking triple -> factoid -> message -> validation events -> responders. Example meta-triples:
  - (factoid_cid, extractedBy, microLLM:vX/promptHash)
  - (factoid_cid, validatedBy, user:<id>)
  - (triple_cid, assertedFrom, factoid_cid)

PII & privacy handling
- Preprocessor MUST detect and redact PII. If PII cannot be safely redacted, route to moderator lane; do not emit public prompts.
- Right-to-be-forgotten: maintain mappings from `msg_cid` to stored artifacts; provide a revocation flow that appends revocation meta-triples and redacts/unlinks content. Note that content-addressed systems need special handling for irrevocable snapshots.

Monitoring & alerts
- Monitor TTL breaches for candidate factoids, backlog depth, and validation latency.
- Alert on high expired rates, frequent schema validation failures, or sustained backlog growth.

Operational playbooks
- Backlog surge: auto-scale Dreaming workers; apply back-pressure to ingestion if backlog exceeds thresholds; notify ops.
- Prompt spam: tighten per-user and per-channel rate limits; rollback prompts and pause actors until verified.

Logging format
- Structured JSON logs MUST use canonical field names and include: `timestamp`, `service`, `level`, `msg_cid` (32-hex if available), `factoid_cid`, `event_id`, `triple_cid`, `request_id`, `trace_id`, `details`.

Example structured error (machine-readable):
```
{
  "code": "invalid_payload",
  "message": "Schema validation failed",
  "details": [{"field":"provenance.msg_cid","error":"required"}],
  "request_id": "...",
  "trace_id": "..."
}
```
```