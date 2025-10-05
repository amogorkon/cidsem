
## 1 — High-level components

### Ingress / Preprocessor
Language detection, redaction (PII), normalization, chunking (overlap).
### Symbolic Extractor (real-time fast path)
Regex, spaCy NER, dependency patterns, deterministic rules → seed predicates.
### Micro-LLM Fallback (real-time optional)
Tiny transformer (<100M params) used for edge-case routing (5–10%).
### Backlog Queue
Durable prioritized queue (Redis streams, SQS, or Kafka) of unresolved / candidate items.
### Dreaming Batch Pipeline
Coref/context resolver, LLM extractors, normalizer, tripleizer, validator, CID mapper.

### Predicate Registry Service
Centralized ontology (predicate URIs, versions, aliases, deprecation, migration scripts).

### CID Mapper & Inserter

Deterministic serializer + BLAKE3-128 → CIDs, and writer into CIDStore (Idx_SP / Idx_PO / Idx_OS) + meta-triples.

### Curation Console

Human review UI for moderator review of candidate predicates, merges, schema promos.

### Monitoring & Governance

Metrics, SLIs, drift detection, shadow testing, alerts.

## 2 — Seed ontology (v0) — 15 predicates (recommended)

|ID|Short name | Description |
|--|-----------|------------|
|1 |posted     | user posted message (system; symbolic)
|2 |mentions   | mentions entity/concept |
|3 |states     | assertive factual claim (S states O) |
|4 |believes   | expresses belief/opinion about O |
|5 |asksAbout  | question/asks about O |
|6 |cites      | references an external source (URL, paper) |
|7 |joined     | joined/started membership/role |
|8 |left       | left/ended membership/role |
|9 |worksAt    | employment relationship |
|10|livesIn    | location/habitation |
|11|hasEvent   | event mention (time-scoped) |
|12|madeClaimAbout | general claim relation (catch-all) |
|13|disagreesWith | contradiction/negation relation |
|14|supports   | supports/endorses another claim or actor |
|15|securityAlert | flagged content for security/moderation (high priority) |

Each predicate has an authoritative URI (e.g. https://tetraplex.org/predicate/hasEvent:v1) and a short description and extraction pattern in the registry.

## 3 — Data schemas (JSON)
### 3.1 Chunk record (preprocessor output)

```json
{
  "chunk_id": "uuid",
  "msg_cid": "bafy...128",           // CIDStore message CID
  "text": "string",
  "lang": "en",
  "char_range": [start, end],
  "chunk_hash": "hex",
  "overlap": true|false
}
```

### 3.2 Backlog item (queue entry)

```json
{
  "item_id": "uuid",
  "chunk": {... chunk record ...},
  "symbolic_candidates": [
    {"predicate":"t:mentions","spans":[[10,15]], "entities":[{"text":"Alice"}]}
  ],
  "symbolic_confidence": 0.0-1.0,
  "route_reason": "symbolic_missing|low_confidence|manual_flag",
  "priority": "critical|high|normal|low",
  "enqueue_ts": "ISO8601",
  "origin": "realtime|replay"
}
```

### 3.3 Factoid JSON (LLM output, strict schema)
```json
{
  "factoid_id": "uuid",
  "factoid_text": "Alice moved to Berlin in summer 2023.",
  "subject_raw": "Alice",
  "object_raw": "Berlin",
  "predicate_candidates": [
    {"predicate_uri": "https://tetraplex.org/predicate/livesIn:v1", "score": 0.82},
    {"predicate_uri": "https://tetraplex.org/predicate/hasEvent:v1", "score": 0.25}
  ],
  "confidence": 0.0-1.0,
  "modality": "assertion|belief|question|speculation|negation",
  "time_scope": {"start":"2023-06-01","end":"2023-09-01"},
  "provenance": {"msg_cid":"bafy...","chunk_id":"uuid","char_range":[0,46]},
  "normalizations": {"subject_cid": null, "object_cid": null},
  "factoid_fp": "hex128"
}
```

Enforce strict validation server-side. If invalid, mark confidence=0 and send to manual queue.

### 3.4 Triple record (post-canonicalization)
```json
{
  "triple_id": "cid128",            // composed triple CID or triple-specific CID
  "subject_cid": "cid128",
  "predicate_uri": "https://tetraplex.org/predicate/livesIn:v1",
  "object_cid": "cid128_or_literal",
  "confidence": 0.0-1.0,
  "provenance": {"factoid_id":"uuid","msg_cid":"bafy...","extracted_by":"model:v1|rules:v1"},
  "schema_version": "predicate:v1",
  "insert_ts": "ISO8601"
}
```
Enforce strict validation server-side. If invalid, mark confidence=0 and send to manual queue.
### 3.5 Predicate registry entry (service)
```json
{
  "predicate_uri": "https://tetraplex.org/predicate/livesIn:v1",
  "label": "livesIn",
  "description": "Person resides in location",
  "version": "v1",
  "aliases": ["schema:livesIn"],
  "extract_pattern": "regex/or dependency pattern",
  "confidence_threshold_realtime": 0.9,
  "allowed_modalities": ["assertion","belief"],
  "owner": "ontology-team",
  "deprecated": false,
  "migration_script": "script_uri or null",
  "created_ts": "ISO8601"
}
```

## 4 — Microservice APIs

All service-to-service comms are JSON-over-HTTP (FastAPI) or gRPC for heavy throughput. Use msgpack for internal high-throughput lanes if desired.

### 4.1 Preprocessor API

POST /preprocess → accepts raw message, returns chunk array and msg_cid if pre-existing.

GET /preprocess/chunks/{chunk_id} → retrieve chunk.

### 4.2 Symbolic Extractor API (real-time)

POST /symbolic/extract
Body: {chunk_id, text, msg_cid}
Returns: {symbolic_candidates: [...], decision: "accept|queue", confidence}

Rule engine returns either decision: accept (auto-insert triple) or queue (enqueue backlog item).

### 4.3 Backlog Queue Interface

Push: queue client pushes BacklogItem with priority.

Pop: batch worker pulls items (supports claim/ack semantics).

Inspect: GET /queue/stats, list by priority.

### 4.4 Dreaming Batch Pipeline API

POST /dream/process_batch with list of item_id. Returns job_id.

GET /dream/job/{job_id} status & metrics.

### 4.5 LLM Service (stateless)

POST /llm/extract_factoids accepts chunk(s), prompt template id, returns array of validated Factoid JSON.

POST /llm/tripleize accepts factoid(s), returns ranked predicate list & canonical suggestions.

Include model version & prompt hash in responses.

### 4.6 Predicate Registry API

GET /predicates (list)

GET /predicates/{predicate_uri}

POST /predicates/propose → for dreaming to propose new predicate (includes sample factoids, support count).

POST /predicates/{predicate_uri}/approve → moderator approves/creates version.

POST /predicates/{predicate_uri}/migrate → runs migration script.

### 4.7 CIDStore Writer

POST /cidstore/insert_triples body: list of TripleRecord. Returns success and inserted triple CIDs.

Include transactional semantics: write should WAL then insert; return per-triple success & reasons.

## 5 — LLM prompt bundle (deterministic JSON output)

Use low temperature (0.0), fixed seed where possible, and strict JSON schema validation. Provide 2–3 few-shot examples.

System instruction (short):

> You are a fact extractor. Given the input text chunk, output a JSON array of canonical factoids. Each factoid must be a single declarative sentence, normalized (ISO dates), and include predicate candidates (URI list). Do not output extra keys. Follow the schema exactly.


**Few-shot example 1**
Input: “John joined Acme as CTO in 2019.”
Output: (as Factoid JSON with predicate_candidates [t:joined, t:worksAt], confidence 0.98).

**Few-shot example 2 (hedged)**
Input: “I think John may move to Berlin next year.”
Output: factoid with modality: speculation, confidence 0.35, time_scope for 2026 (approx), and suggestions.

Validate response against JSON Schema server-side. If parsing fails, retry once with same prompt; if still fail, log and route to manual review.

## 6 — Normalizer & Canonicalizer

Steps

1. Named Entity Resolution: map subject_raw/object_raw via resolver (fuzzy match, Wikidata, local registry). Return subject_cid or null.
2. Date normalization: parse human times into ISO ranges (use dateparser).
3. Literal canonicalization: numbers, units normalized.
4. If mapping fails, create provisional CIDs (= content-based CID of normalized token) but mark provisional:true.

**Resolver strategy**

* Local alias table first (fast).
* Fallback to external resolver (Wikidata) only in dreaming (not real-time).
* Record resolution provenance and score.

## 7 — Confidence & Scoring rules

**Real-time**

* If symbolic extraction produced a match → confidence = 0.99; insert triple with schema_version set to the active registry version.
* If symbolic uncertain (low regex score) → route to backlog.

**Dreaming**

`final_confidence = clamp( w_llm * llm_conf + w_sym * sym_conf + w_res * resolver_score + w_time * time_score )`

Default weights: `w_llm=0.55, w_sym=0.25, w_res=0.15, w_time=0.05 (tune after rollout).`

Thresholds:

>=0.85: auto-assert triple (write to CIDStore with provenance).

0.5–0.85: insert as candidate (candidate:true) with lower query rank.

<0.5: hold for further corroboration/dreaming.

Confidence decay

Apply half-life decay of confidence for time-scoped factoids unless re-asserted or corroborated.

8 — Backlog / Prioritization & SLAs

Priority classes

critical (security/moderation): SLA process in 5 min.

high (high-karma messages, admin flagged): SLA 1 hour.

normal: SLA 12–24 hours.

low: SLA 72 hours or batch window.

Queue processing

Workers claim items and must ack within visibility timeout. Use concurrency limits.

If backlog > threshold (e.g., 10k items), auto-scale workers or throttle ingestion.

Metrics & alerts

Backlog size > 10k → alert (ops)

Max age > SLA → alert

Dreaming job failure rate > 1% → alert

Symbolic vs. Dreaming divergence > 5% → alert (ontology team)

9 — Shadow testing & drift detection

Nightly job:

Replay random sample of real-time auto-inserted triples through the dreaming pipeline.

Compute divergence metrics:

Predicate mismatch rate

Subject/object resolution mismatch

Confidence delta distribution

If any metric exceeds threshold (configurable, default 5%), create a drift ticket and schedule a rule review.

10 — Monitoring & Observability

Dashboards

Ingestion throughput (chunks/sec), backlog depth, dream throughput (factoids/hour), real-time hits per predicate.

Per-predicate extraction precision/recall (from sampled human labels).

LLM cost & token usage by model/version.

Queue SLA heatmap.

Logs & Traces

Correlate traces across services using msg_cid and factoid_fp.

Store prompt_hash & model_version for every inference (for reproducibility).

11 — Testing & evaluation

Datasets

Gold set: 2k–5k annotated messages → factoid & triple ground truth. (Start with 200–500, expand).

Adversarial set: hedging, sarcasm, ellipsis.

Long-context set: multi-message coref cases.

Tests

Unit tests for symbolic rules (expected matches).

Integration tests for LLM service (schema compliance).

End-to-end tests: ingest → extract → normalize → insert (on staging CIDStore).

Regression tests in CI triggered on predicate registry changes.

Evaluation metrics

Precision / Recall / F1 per predicate.

Confidence calibration (reliability plots).

Latency (real-time: <100ms per message; backlog ingestion: <10ms enqueue).

Dream throughput (factoids/hour) and cost per factoid.

12 — Security, privacy & compliance

PII redact in preprocessor: phone numbers, national IDs masked or removed per policy.

Sensitive factoids flagged & stored with restricted access (encryption-at-rest; ACLs).

Audit logs immutable (CIDStore + WAL) to support compliance and GDPR requests (right-to-be-forgotten must map to deletion or unlinking flows).

Minimal raw text retention in dreaming; store only provenance references to message CID where possible.

13 — Deployment topology & infra

Services (containerized):

Preprocessor + Symbolic Extractor Service (FastAPI)

Micro-LLM service (ONNX/ggml runtime) — small model (<100M) for fallback

LLM service for dreaming (GPU-backed, 1–3B models)

Dreaming batch workers (Kubernetes Jobs)

Predicate Registry (database-backed, Postgres)

Backlog Queue (Redis streams / Kafka)

CID Mapper/Inserter (interfaces to CIDStore)

Curation Console (web UI)

Monitoring stack (Prometheus + Grafana + alertmanager)

Scaling

Real-time services scale horizontally behind API gateway.

Dreaming scaled via worker pool with GPU autoscaling for LLM tasks.

Use spot/preemptible GPU capacity for cost efficiency (if acceptable).