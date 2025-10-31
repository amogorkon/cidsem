# 2. Data Structures and Types

---

## 2.0 Core Principles and Key Components

### Pure Content Addressability
- All entities (data, metadata, schemas) are content-addressed via 256-bit entity IDs (E format)
- E entities have four 64-bit fields compatible with cidstore.E class: high, high_mid, low_mid, low
- Uses SHA-256 for deterministic E generation (JACK hash format: "E(h,hm,lm,l)")
- No distinction between data, metadata, or schemas—all are E entities

### Schema-First Architecture
- Schemas are first-class content with their own CIDs
- Schemas define binary layout, not just semantics
- Schema implementations enable zero-deserialization access

### Performance-Centric Design
- Fixed binary formats for vectorized/SIMD processing
- Schema-specific indexing (range, fulltext, spatial)
- Memory-mapped direct access to avoid parsing

| Component     | Specification                        | E Entity Handling                            |
|--------------|--------------------------------------|----------------------------------------------|
| Meta-Schema  | Pre-seeded fixed schema              | Hardcoded known E (high/low)                |
| Schemas      | Canonical JSON defining binary layout | E = SHA3_128(canonical_json)                 |
| Data Records | Binary blobs following schema         | E = SHA3_128(schema_e + binary_data)         |
| Triples      | (subject_e, predicate_e, object_e)   | Output format for cidstore insertion         |

---

## 2.1 Content Addressing Model

All data in CIDSEM is mapped to a 256-bit Entity identifier (E), computed as a SHA-256 hash over its canonical form, compatible with cidstore.E format. This ensures:
- **Deterministic addressing**: Identical content always produces the same E entity
- **Content verification**: E entities serve as integrity checksums
- **Deduplication**: Identical content is stored only once
- **cidstore compatibility**: E entities can be directly used as keys/values in cidstore

### E Entity Representation
CIDs are represented in multiple formats:
- **String format**: `"E(h,hm,lm,l)"` where h, hm, lm, l are four 64-bit unsigned integers
- **List/Tuple**: `[high, high_mid, low_mid, low]` as a 4-element array
- **JACK hexdigest**: `"j:abcd..."` string (converted to E numeric form by cidstore)
- **Struct format**: `{"high": uint64, "high_mid": uint64, "low_mid": uint64, "low": uint64}`

### Canonical Forms
- **Schemas**: Canonicalized JSON (following RFC 8785)
- **Metadata**: Byte-represented fixed-width uint arrays
- **Content**: Original byte representation with deterministic serialization

## 2.2 Triple Output Format (cidstore compatibility)

All cidsem output must be formatted as triples compatible with cidstore insertion. Each triple element is a 128-bit E entity.

### Triple Structure
```python
# Triple format: (subject: E, predicate: E, object: E)
# All elements are cidstore.E instances or dicts with high/low fields
```

### E Entity Format
- **E class**: 256-bit entity with four 64-bit fields: `high`, `high_mid`, `low_mid`, `low`
- **Creation**: Uses SHA-256 hashing over canonical content
- **Serialization**: `{"high": uint64, "high_mid": uint64, "low_mid": uint64, "low": uint64}` for msgpack/JSON
- **String format**: `"E(high,high_mid,low_mid,low)"` for human-readable representation
- **cidstore integration**: Direct use in ZMQ/msgpack messages for batch operations

### Context-to-Triple Examples
```python
# Input context: {"user": "alice", "action": "login", "timestamp": "2024-06-01T12:00:00Z"}
# Output triples (256-bit E format):
triples = [
  {
    's': 'E(12345,67890,11121,31415)',      # alice (subject)
    'p': 'E(23456,78901,21222,41516)',      # performed (predicate)
    'o': 'E(34567,89012,31323,51617)'       # login (object)
  },
  {
    's': 'E(12345,67890,11121,31415)',      # alice (subject)
    'p': 'E(45678,90123,41424,61718)',      # timestamp (predicate)
    'o': 'E(56789,01234,51525,71819)'       # 2024-06-01T12:00:00Z (object)
  }
]
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

Additional fields and decisioning metadata (integrated)

- `CandidateFactoid` should include: `factoid_cid` (content-address where possible), `status` (pending_validation | confirmed | rejected | expired), `priority` (critical|high|normal|low), `created_ts`, `expires_at`, and `provenance` including `msg_cid`, `chunk_id`, `extractor_ver`, and `prompt_hash`.
- `ValidationEvent` records `event_id`, `factoid_cid`, `responder_id` (user/moderator/system), `response` (confirmed|rejected|abstain), `bot_id` (if applicable), `prompt_hash`, `model_version`, and `timestamp`.
- `BacklogItem` must reference `factoid_cid`, include reprocessing metadata, `priority`, and `validation_history` links.

Provenance model

Every stage of the pipeline must be traceable via meta-triples in CIDStore. Example meta-triples:

 - (factoid_cid, extractedBy, microLLM:vX/promptHash)
 - (factoid_cid, validatedBy, userCID)
 - (factoid_cid, validationEventCID, eventCID)
 - (triple_cid, assertedFrom, factoid_cid)

This enables walkable chains: triple -> factoid -> message -> validation events -> responders.

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

TripleRecord (cidstore-compatible, 256-bit format)
```
{
  "subject": {"high": 12345, "high_mid": 67890, "low_mid": 11121, "low": 31415},
  "predicate": {"high": 23456, "high_mid": 78901, "low_mid": 21222, "low": 41516},
  "object": {"high": 34567, "high_mid": 89012, "low_mid": 31323, "low": 51617},
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