# 5. Schema Registry, Dispatch, and Node Initialization

## 5. Schema Registry & Dispatch
A schema registry maps schema CIDs to their handler logic.

Registry may be implemented via:
- Central microservice (e.g., RESTful)
- Distributed KV store (e.g., etcd, Consul)

**Registry entry format:**
```json
{
  "cid": "abc123...",
  "handler_url": "https://cidsem.io/handlers/abc123.py",
  "entrypoint": "dispatch",
  "language": "python",
  "version": "1.0.3"
}
```markdown
# Components and functionality

This file expands the responsibilities and contracts of the primary services.

Preprocessor / Ingress
- Responsibilities: accept raw messages, language detection, PII redaction, normalization (unicode, whitespace), chunking with overlap, compute `chunk_hash`, assign or discover `msg_cid`.
- Outputs: `Chunk` records and `msg_cid`.

Symbolic Extractor (real-time)
- Responsibilities: apply deterministic extraction rules (regex, dependency patterns, NER), produce `TripleRecord` for high-confidence matches, or mark `BacklogItem` for ambiguous cases.
- Contract: return `{decision: "accept"|"queue", candidates: [...] , confidence: 0.0-1.0}` within latency <100ms.

Micro-LLM Fallback (real-time)
- Responsibilities: lightweight transformer for ambiguous chunks to generate `CandidateFactoid` JSON. Never auto-assert into CIDStore.
- Contract: output deterministic JSON (prompt_hash + model_version) with `predicate_candidates` and `confidence`.

Validation Layer (Bot Services + Worker)
- Barkeep, Critic, Historian personas produce prompts from `CandidateFactoid` records. Collect `ValidationEvent` responses and run the decision algorithm (priority, TTL, weights) to confirm/reject/expire.
- Side-effects: on confirmed -> generate (subject: E, predicate: E, object: E) triples and call cidstore.insert(); on rejected/expired -> Backlog for Dreaming.

Bot personas and prompting rules (integrated)

- Barkeep: friendly, minimal-friction; used to ping authors for quick yes/no confirmation (one-click responses).
- Critic: contradiction-check persona used when a candidate contradicts known high-confidence triples; asks targeted questions and references conflicting evidence.
- Historian: community confirmation persona for broad claims where multiple confirmations are required.

Prompting policy:

- Only surface high-value/novel/ambiguous factoids; attach minimal context (source sentence, `msg_cid`, 1-line LLM justification) and include one-click responses (Yes/No/Not sure).
- Rate-limit prompts per user and per channel; respect user opt-out and PII redaction rules.

Backlog Queue & Dreaming (integrated)
- Backlog items (durable queue entries) capture rejected/expired candidates and symbolic misses. Workers claim items (GET /backlog/claim) and process them in batches.
- Dreaming Batch Pipeline performs coreference resolution, full LLM extraction, normalization, context-to-triple extraction (outputting E entity triples), and proposes canonical triples and predicate suggestions to the Predicate Registry.

Predicate Registry (integrated)
- Central registry holds predicate entries with metadata: `predicate_uri`/`predicate_cid`, versioning, confidence thresholds, allowed modalities, aliases, and migration scripts.
- Dreaming may propose new predicates through `POST /predicates/propose`; moderators approve via `POST /predicates/{predicate_uri}/approve` and migration scripts run via `POST /predicates/{predicate_uri}/migrate`.

CID Mapper & Inserter (integrated)
- Deterministic E entity generation (SHA3/UUID5) for all triple elements. Converts contexts to (subject: E, predicate: E, object: E) format. Uses cidstore.insert(key, value) for batch insertion where key and value are both E entities representing parts of triples. Must be idempotent and stateless.

Backlog Queue & Dreaming
- Backlog: durable prioritized queue; items include rejected/expired candidate factoids and symbolic misses.
- Dreaming Batch Pipeline: coreference resolution, full LLM extraction, tripleizer, canonicalizer, and suggestions to predicate registry.

Predicate Registry
- Centralized service with predicate URIs, versions, aliases, confidence thresholds, allowed modalities, owner, and migration scripts.
- Supports propose/approve/migrate endpoints used by Dreaming and moderators.

CID Mapper & Inserter
- Deterministic canonicalizer and CID generation (e.g., BLAKE3-128). Inserts are WAL-backed and idempotent; returns per-triple status and inserted `triple_cid` (CID).

Curation Console
- UI for moderators/curators: shows CandidateFactoid + LLM justification, validation history, quick actions (Confirm / Reject / Send to Dreaming / Request Evidence).

Monitoring & Governance
- Dashboards for throughput, latency, backlog size, resolution latency, expired rate, labeled-data generation rate, and user fatigue metrics.

Operational constraints
- Rate-limits: configurable per-user and per-channel; default safe values should be documented in runtime config.
- Privacy: preprocessor must detect and handle PII before any public prompt is emitted.
```
