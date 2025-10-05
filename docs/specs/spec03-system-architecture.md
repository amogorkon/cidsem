# 3. System Architecture: Content Addressability, Schema-First, and Performance

## 3.1 Core Principles

### Pure Content Addressability
- Everything is content-addressed via CIDs (e.g., xxhash.xxh128 or similar)
- No distinction between data, metadata, or schemas—all are CIDs
- Deterministic CID generation through canonicalization (e.g., RFC 8785 for JSON)

### Schema-First Architecture
```markdown
# System architecture (overview)

This document summarizes the system-level architecture aligned to the proposed extraction and validation pipeline. It emphasizes modular services, content-addressed artifacts, provenance, and safe deployment via the Validation Layer.

High-level flow

flowchart LR
  Raw[Raw Messages] --> Pre[Preprocessor / Chunker]
  Pre --> Sym[Symbolic Extractor (real-time)]
  Sym -->|high-confidence| CIDIns[CIDStore Insert]
  Sym -->|ambiguous| Micro[Micro-LLM Fallback]
  Micro -->|candidate| CF[CandidateFactoid]
  CF --> Val[Validation Layer]
  Val -->|confirmed| CIDIns
  Val -->|rejected| Back[Backlog / Dreaming]
  Back --> Dream[Dreaming Batch (LLM + Coref)]
  Dream --> CIDIns

Core system components
- Preprocessor / Chunker: language detection, redaction, chunking, and chunk-level hashing.
- Symbolic Extractor: deterministic rules, dependency patterns, and NER for high-confidence auto-assertions.
- Micro-LLM Fallback: tiny transformer for ambiguous extractions; outputs CandidateFactoids (never auto-inserted).
- Validation Layer: bot services + human/community prompts, consensus rules, TTLs, and audit logs.
- Backlog / Dreaming: prioritized durable queue and batch LLM pipeline for reprocessing and predicate discovery.
- Predicate Registry: ontology service with predicate URIs, versions, aliases, deprecation and migration scripts.
- CID Mapper & Inserter: canonicalization, CID generation (e.g., BLAKE3-128), and WAL-backed insertion into CIDStore with meta-triples.
- Curation Console: human interfaces for moderators and curators to inspect factoids, votes, and to perform bulk actions.
- Monitoring & Governance: metrics, SLIs, drift detection, shadow testing, and alerting.

Deployment considerations
- Real-time services are horizontally scalable and latency-sensitive; Dreaming uses GPU-backed workers for LLM tasks.
- Use a durable queue (Redis Streams, Kafka, SQS) for backlog and claim/ack semantics.
- Record prompt_hash, model_version, and msg_cid for every inference for reproducibility.

Pilot strategy
- Start with 1–2 high-value predicates (e.g., `t:joined`, `t:worksAt`) on a small user subset.
- Run symbolic extractor in production shadow mode for other predicates; route micro-LLM candidates to a staging validation loop.
```
### Zero-Cost Access
