```markdown
# API design & interfaces (summary)

All service-to-service communications are JSON-over-HTTP (FastAPI) for control endpoints and optional gRPC for high-throughput lanes. Internal high-throughput lanes may use msgpack over binary streams.

Guiding principles
- Strict input validation server-side using JSON Schema.
- All inference responses include `model_version` and `prompt_hash`.
- Endpoints are idempotent where appropriate and return machine-readable error payloads. POST endpoints should accept an optional `Idempotency-Key` header; server-side WAL ensures safe retries and deduplication.

Key endpoints

POST /candidate_factoids
- Producer: micro-LLM fallback or Dreaming suggestions.
- Body: `CandidateFactoid` (see schema). Servers MUST validate against the JSON Schema and reject with 400 when invalid.
- Request headers: optional `Idempotency-Key: <hex>` (clients SHOULD set to make POST idempotent across retries).
- Response: 201 { "factoid_cid": "<32hex>" } or 400/409/422 with machine-readable error (see Error model).
- Side-effects:
  - Write a WAL record with the incoming CandidateFactoid and `Idempotency-Key` (if provided).
  - If the factoid passes priority/threshold rules, enqueue a validation job onto the backlog (BacklogItem) with `item_id` referencing the factoid.
  - Return immediately after WAL write succeeds; job dispatch to workers is eventual.

GET /validation_prompt/{factoid_cid}
- Returns prompt text and JSON payload for a bot persona to post into chat. Includes minimal context: source sentence, msg link (`msg_cid`), predicate candidates, current validation history, and LLM justification. Response 200 with `{prompt, factoid_cid, candidates, provenance}`.

POST /validation_event
- Body: `ValidationEvent` (see schema). Request SHOULD include `Idempotency-Key` for client retries.
- Side-effects: append ValidationEvent to WAL, recompute validation decision (consensus, TTL, weights). If the result is `confirm` -> extract (subject: E, predicate: E, object: E) triples from confirmed factoid, serialize as msgpack with 256-bit E fields (high, high_mid, low_mid, low), and send via ZMQ batch_insert to cidstore with optimized batching (32-1024 items) using REQ/REP or PUSH/PULL patterns. If `reject` or `expire` -> push `BacklogItem` to backlog queue.
- Performance: Auto-tune batch size based on observed latency; target <100μs P99 for validation processing.
- Error Recovery: Retry failed cidstore inserts with exponential backoff; ValidationEvents are idempotent and safe to replay.

GET /backlog/claim
- Workers call this to pop/claim backlog items for Dreaming. Supports claim/ack semantics and visibility timeouts.

POST /dream/process_batch
- Accepts list of `item_id` and returns `job_id` for asynchronous Dreaming runs. Dreaming output may include `CandidateFactoid` or `TripleRecord` suggestions and predicate proposals (via `POST /predicates/propose`).

Predicate Registry API
- GET /predicates — list registry entries.
- GET /predicates/{predicate_uri} — get entry.
- POST /predicates/propose — Dreaming proposes new predicate with sample factoids and support count.
- POST /predicates/{predicate_uri}/approve — moderator approves/creates new version.
- POST /predicates/{predicate_uri}/migrate — run migration script for existing triples.

POST /cidstore/batch_insert
- **DEPRECATED**: This REST endpoint is for legacy compatibility only. Use ZMQ data plane for production.
- Body: msgpack-encoded array of `{"key": {"high": uint64, "high_mid": uint64, "low_mid": uint64, "low": uint64}, "value": {"high": uint64, "high_mid": uint64, "low_mid": uint64, "low": uint64}}`.
- Response: `201 { results: [{status:"ok"|"error", message:""}], performance: {latency_ms: float, throughput_ops_sec: int} }`
- Semantics: Maps to cidstore insert operations; idempotent; WAL-backed by cidstore internally.
- **Recommended**: Use ZMQ batch_insert instead for production workloads.

CIDStore ZMQ Integration (Recommended)
- Primary: ZMQ REQ/REP on tcp://cidstore:5555 with msgpack batch_insert messages
  - Request: `{"command": "batch_insert", "triples": [{"s": "E(h,hm,lm,l)", "p": "E(...)", "o": "E(...)"}]}`
  - Response: `{"status": "ok", "inserted": <count>, "version": "1.0"}`
- Production: ZMQ PUSH/PULL on tcp://cidstore:5557 for fire-and-forget high throughput
  - Message: `{"op_code": "BATCH_INSERT", "entries": [{"key": "E(...)", "value": "E(...)"}]}`
- Performance: Target >1M ops/sec (batched), adaptive batch sizing 32-1024 items, <50μs average latency.
- Error Recovery: Exponential backoff retry on network errors, partial failure re-send of failed items only.
- See: docs/specs/spec11-cidstore-integration.md for complete integration guide

POST /validation_event
- Body: `ValidationEvent` (see schema). Request SHOULD include `Idempotency-Key` for client retries when user action is re-sent by the client.
- Response: 200 {"status":"accepted","factoid_cid":"<32hex>","applied":true|false}
- Side-effects:
  - Append the ValidationEvent to WAL and validation history for the `factoid_cid`.
  - Recompute validation decision (consensus, TTL, weights) per `validation_decision_pseudocode.md`.
  - If decision is to assert: build `TripleRecord`(s), compute `triple_cid`(s), write to CIDStore via `POST /cidstore/insert_triples` (WAL-first). Return applied=true once WAL and insert request were queued; final per-triple status is available via CIDStore response or a separate async status endpoint.
  - If decision is to reject or expire: create a `BacklogItem` and queue for Dreaming.

GET /backlog/claim
- Workers call to pop/retrieve backlog items (supports claim/ack).

POST /dream/process_batch
- Accepts list of `item_id` and returns `job_id` for asynchronous dream runs.

GET /predicates
- List predicate registry entries.

POST /predicates/propose
- Dreaming proposes new predicate with sample factoids and support count; moderators approve via `/predicates/{predicate_cid}/approve` (APIs MAY also accept legacy `predicate_uri` values for compatibility).

POST /cidstore/insert_triples
- Body: list of `TripleRecord`.
- Response: `201 { results: [{triple_cid:"<32hex>", status:"ok"|"error", code:, message:}] }`
- Semantics:
  - WAL-first: writer writes a WAL record containing the payload and request metadata (`request_id`, `Idempotency-Key`) before attempting physical insert.
  - Idempotent: repeated requests with same `Idempotency-Key` and request payload must not produce duplicate asserted triples; WAL is consulted to suppress duplicates and return prior results.
  - Best-effort transactional semantics: the endpoint returns per-triple results; a partial failure returns 200 with detailed per-triple statuses or 207 Multi-Status if supported by client and server.
  - Retries: clients SHOULD retry idempotently; server SHOULD expose `request_id` and `trace_id` on error responses for debugging.

Error model
- 4xx: client validation errors (schema mismatch, missing fields) — Response `400` with JSON `{ "code": "invalid_payload", "message": "Schema validation failed", "details": [{"field":"provenance.msg_cid","error":"required"}, ...] }`.
- 409: conflict due to idempotency (duplicate `Idempotency-Key` with non-matching payload) — `{ "code":"idempotency_conflict", "message":"Idempotency key conflict" }`.
- 422: semantic rejection (payload valid but violates business rules) — `{ "code":"semantic_rejection", "message":"predicate not allowed for this predicate_cid", "details": {...} }`.
- 502: cidstore integration errors — `{ "code":"cidstore_error", "message":"cidstore insertion failed", "cidstore_details": {...}, "retry_suggested": true }`.
- 503: performance degradation — `{ "code":"performance_limit", "message":"throughput limit exceeded", "current_ops_sec": 800000, "target_ops_sec": 1000000, "retry_after_ms": 100 }`.
- 5xx: server errors — `{ "code":"internal_error", "message":"something went wrong", "request_id":"<uuid>", "trace_id":"<trace>" }`.
- All error responses MUST be JSON and include `request_id` (server-generated) for tracing and performance metrics.

Security
- All endpoints require authentication and fine-grained authorization for moderator-level actions (predicate approve, moderator override).

Example contract (POST /candidate_factoids)
- Input: CandidateFactoid v1 (required fields: `factoid_cid` or `factoid_fp` (legacy fingerprint), `subject_raw`, `predicate_candidates[]` (each candidate SHOULD include `predicate_cid`; servers MAY accept `predicate_uri` as a legacy alias), `confidence`, `provenance:{msg_cid, chunk_id}`, `model_version`, `prompt_hash`).
- Output: 201 { "factoid_cid": "<32hex>" }.
- Side-effects: enqueues validation job if configured to do so.
```
# 7. Ingestion Flow

Incoming triple is split into:
- Subject (uint array)
- Predicate (uint array)
- Object (uint array)

Each component’s first uint is used to identify its schema (by enum or CID).
Node locates or downloads the schema from cidstore (CID → content).
Node fetches handler implementation (via local cache or registry lookup).
Metadata array is dispatched to handler:
  - Validates
  - Indexes values (for range, graph ops, etc.)
  - Produces metadata CID

CID → content mappings and relationships are written to:
- cidstore (e.g., Redis)
- semantic layer (triples indexed via CID)
