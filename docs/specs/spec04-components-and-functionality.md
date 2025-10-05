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
- Side-effects: on confirmed -> CIDMapper/Inserter; on rejected/expired -> Backlog for Dreaming.

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
