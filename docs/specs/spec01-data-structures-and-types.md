# 2. Data Structures and Types

---

## 2.0 Core Principles and Key Components

### Pure Content Addressability
- All entities (data, metadata, schemas) are content-addressed via CIDs (e.g., xxhash.xxh128)
- Deterministic CID generation through canonicalization
- No distinction between data, metadata, or schemas—all are CIDs

### Schema-First Architecture
- Schemas are first-class content with their own CIDs
- Schemas define binary layout, not just semantics
- Schema implementations enable zero-deserialization access

### Performance-Centric Design
- Fixed binary formats for vectorized/SIMD processing
- Schema-specific indexing (range, fulltext, spatial)
- Memory-mapped direct access to avoid parsing

| Component     | Specification                        | CID Handling                                 |
|--------------|--------------------------------------|----------------------------------------------|
| Meta-Schema  | Pre-seeded fixed schema              | Hardcoded known CID                          |
| Schemas      | Canonical JSON defining binary layout | CID = hash(canonical_json)                   |
| Data Records | Binary blobs following schema         | CID = hash(schema_cid + binary_data)         |
| Triples      | (subject_cid, predicate_cid, object_cid) | CID = hash(subject|predicate|object)     |

---

## 2.1 Content Addressing Model

All data in CIDSEM is mapped to a Content Identifier (CID), computed as a cryptographic hash over its canonical form. This ensures:
- **Deterministic addressing**: Identical content always produces the same CID
- **Content verification**: CIDs serve as integrity checksums
- **Deduplication**: Identical content is stored only once
- **Distributed caching**: Content can be safely cached and shared across nodes

### Canonical Forms
- **Schemas**: Canonicalized JSON (following RFC 8785)
- **Metadata**: Byte-represented fixed-width uint arrays
- **Content**: Original byte representation with deterministic serialization

## 2.2 Metadata Encoding

Metadata for subjects, predicates, and objects is encoded as **fixed-width arrays of unsigned integers**. This design provides several key benefits:

### Design Principles
- **SIMD-friendly**: Fixed-width arrays enable vectorized operations
- **Cache-efficient**: Predictable memory layout improves cache performance
- **Hash-optimized**: Fixed-size structures enable fast batch hashing
- **Schema-driven**: First element identifies the schema for interpretation

### Metadata Structure
```
[schema_ref, field1, field2, ..., fieldN]
```

Where:
- `schema_ref`: Numeric schema reference (schema CID hash or enum)
- `field1...fieldN`: Schema-defined field values encoded as uints

### Encoding Examples
```ini
# Person subject
Subject    = [1, 123, 19850615, 42]
# schema_ref=1 (person), person_id=123, birth_date=19850615, nationality=42

# "hasAge" predicate
Predicate  = [2, 5, 1]
# schema_ref=2 (temporal_relation), relation_type=5, temporal_context=1

# Age value object
Object     = [3, 456, 25, 20241201]
# schema_ref=3 (numeric_value), value_id=456, value=25, timestamp=20241201
```

```markdown
# Data structures & types (summary)

This file enumerates the primary machine-readable artifacts and their purpose. Each artifact must be expressed as a versioned JSON Schema in `docs/spec/schemas/` (recommended). The examples below describe the canonical fields and intent; implementers should produce exact JSON Schema files from these definitions.

Core artifacts
- `Chunk` — preprocessor output (a normalized slice of message text).
- `CandidateFactoid` / `Factoid` — LLM-produced candidate assertions with predicate candidates and provenance.
- `ValidationEvent` — a recorded user/bot response to a validation prompt.
- `BacklogItem` — queue entry for dreaming or reprocessing.
- `TripleRecord` — canonical triple ready for CIDStore with provenance and schema_version.
- `PredicateRegistryEntry` — registry metadata for predicates (URI, versions, thresholds, migration script).

Design principles
- All artifacts include a stable identifier (CID where deterministic canonicalization is possible, otherwise UUID) and provenance pointing to `msg_cid` and `chunk_id`.
- All inference outputs must include `model_version` and `prompt_hash`.
- Confidence values are floating point in [0.0, 1.0].
- Schemas are versioned and immutable; changes create new schema versions (predicate:v1 → predicate:v2).

Canonical examples (compact)

Chunk
```
{
  "chunk_id": "uuid",
  "msg_cid": "bafy...",
  "text": "string",
  "language": "en",
  "char_range": [start, end],
  "chunk_hash": "hex128",
  "overlap": true|false
}
```

CandidateFactoid
```
{
  "factoid_cid": "uuid_or_cid",
  "factoid_text": "single declarative sentence",
  "subject_raw": "string",
  "object_raw": "string",
  "predicate_candidates": [{"predicate_cid":"cid:pred:t:...","score":0.0-1.0}],
  "confidence": 0.0-1.0,
  "modality": "assertion|belief|question|speculation|negation",
  "time_scope": {"start":ISO8601,"end":ISO8601}|null,
  "provenance": {"msg_cid":"...","chunk_id":"...","extractor":"microllm:v0.1"},
  "normalizations": {"subject_cid":null,"object_cid":null},
  "factoid_fp": "hex128"  # legacy fingerprint; prefer `factoid_cid` where available
}
```

ValidationEvent
```
{
  "event_id": "uuid",
  "factoid_cid": "uuid_or_cid",
  "responder_id": "user:alice|moderator:xyz|system",
  "response": "confirmed|rejected|abstain",
  "timestamp": ISO8601,
  "bot_id": "barkeep|critic|historian|null",
  "prompt_hash": "hex",
  "model_version": "microllm:v0.1"
}
```

TripleRecord
```
{
  "triple_cid": "cid128",
  "subject_cid": "cid128",
  "predicate_cid": "cid:pred:t:...",
  "object_cid": "cid128_or_literal",
  "confidence": 0.0-1.0,
  "provenance": {"factoid_cid":"...","msg_cid":"...","extracted_by":"model:v1|rules:v1"},
  "schema_version": "predicate:v1",
  "inserted_at": ISO8601
}
```

PredicateRegistryEntry (summary)
```
{
  "predicate_cid": "cid:pred:t:livesIn:v1",
  "predicate_uri": "https://tetraplex.org/predicate/livesIn:v1",  # optional legacy alias; prefer `predicate_cid`
  "label": "livesIn",
  "description": "Person resides in location",
  "version": "v1",
  "confidence_threshold_realtime": 0.9,
  "allowed_modalities": ["assertion","belief"],
  "owner": "ontology-team",
  "deprecated": false,
  "migration_script": null
}
```

Notes
- Implementers should create strict JSON Schema files for each artifact and store them under `docs/spec/schemas/` with versioned filenames (e.g., `candidate_factoid.v1.json`).
```