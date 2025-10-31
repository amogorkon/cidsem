# 1. Overview
cidsem is designed as the semantic interface for a triple store system. Its role is to process and map data elements (content, predicates, and related metadata) to deterministic content identifiers (CIDs) without recalculating hashes for large content every time a query is executed. This is achieved by mapping a metadata-derived fingerprint (or summary) of the content to a CID. As such, cidsem sits between a lower level key-value store (e.g., Redis mapping CID → full content) and a higher-level reasoning/query layer built atop a storage relation manager (cidstore).

# 2. Objectives

**Deterministic Mapping:** Convert content and associated metadata into CIDs using a canonical serialization and hashing mechanism (e.g., SHA-128). Consistency is paramount so that identical metadata always produces the same CID.

**Performance Optimization:** Avoid expensive re-hashing of large content on every query by using concise metadata, which includes all required context and ordering information. Support efficient query execution, including range queries on orderable fields (e.g., height, age).

**Modularity:** Separate the semantic responsibilities (mapping and indexing of metadata) from the low-level storage (cidstore) and high-level reasoning logic. This ensures clean boundaries and extensibility.


## objectives

## 0. Content Addressing Model
All data is mapped to a CID, computed as a hash over its canonical form (e.g., canonical JSON for schemas, or byte-represented metadata).

The system avoids recalculating large data hashes at runtime by mapping metadata → CID, where metadata is a fixed-size uint array encoding.

## 1. Metadata Encoding
Metadata for subjects, predicates, and objects is encoded as fixed-width arrays of uints.

The first entry in each array is a numeric schema reference (either a schema CID or enum).

Arrays are designed for SIMD-friendly storage and hashing.

**Example:**
Subject    = [0, 123, 161803398, 42]
Predicate  = [1, 5, 1]
Object     = [2, 456, 314159265, 84]
```markdown
# CIDSEM — Context-to-Triple Extraction for cidstore

This repository defines the CIDSEM specification: a semantic extraction module that transforms arbitrary input contexts (structured or semi-structured data, events, documents, records) into triples suitable for storage in cidstore.

## Core Purpose
cidsem serves as a preprocessing layer that:
- Ingests arbitrary "context" objects (JSON, dicts, events, logs, documents, etc.)
- Extracts meaningful entities and relationships
- Outputs (subject: E, predicate: E, object: E) triples where all elements are 256-bit cidstore.E entities (SHA-256, 4×64-bit parts)
- Provides triples ready for direct insertion into cidstore via ZMQ/msgpack data plane
- Uses msgpack-encoded messages over ZeroMQ for high-performance bulk operations (target >1M ops/sec)
- REST control API (port 8000) for health checks, metrics, and runtime configuration

## Extraction Paths
The system is organized around two complementary extraction approaches:

- Real-time symbolic extraction: deterministic, low-latency rules and pattern matchers that can auto-generate high-confidence triples from structured contexts.
- Dreaming batch pipeline: higher-latency LLM-based extraction + coreference that produces curated candidate triples from complex or ambiguous contexts.

Between these paths sits the Validation Layer: a human-and-bot mediated loop that prevents low-confidence LLM outputs from being auto-inserted while producing high-quality labeled data for retraining.

Goals
- Deterministic, context-to-triple extraction with 256-bit E entities (SHA-256) for cidstore compatibility.
- Clear machine-readable schemas for all artifacts (chunk, factoid, triple, validation event, backlog item, predicate entry).
- Strong provenance and auditability: every cidstore triple links back to the originating context, factoid, and validation event(s).
- Safe rollout via a validation loop and pilot predicates to minimize harm from hallucination or PII exposure.
- Idempotent extraction: same context always produces same (subject: E, predicate: E, object: E) triples.

Audience and intent
- This spec is a living design for engineers building the ingestion, extraction, validation, and insertion pipeline; product/UX for curator flows; and ML teams that consume labeled events for retraining.

## cidstore Integration
cidsem is designed as a preprocessing module for cidstore:
- Uses cidstore.E class for all entity identifiers (256-bit SHA-256 with four 64-bit fields: high, high_mid, low_mid, low)
- Outputs triples as (subject: E, predicate: E, object: E) tuples in msgpack format
- Primary integration via ZMQ REQ/REP endpoint (tcp://<host>:5555) using `batch_insert` command
- High-throughput production path via ZMQ PUSH/PULL (tcp://<host>:5557) for mutation queue
- REST control API (http://<host>:8000) for health checks (/health, /ready), metrics (/metrics), and runtime config
- Leverages cidstore's WAL, multi-value support, and HDF5 backend for persistence
- Performance targets: >1M ops/sec (batched), <50μs average latency, <100μs P99

## Context-to-Triple Examples
```python
import zmq
import msgpack

# Input context
context = {
  "user": "alice",
  "action": "login",
  "timestamp": "2024-06-01T12:00:00Z"
}

# Output triples (256-bit E format with 4×64-bit parts)
triples = [
  {
    's': 'E(12345,67890,11121,31415)',    # alice (subject)
    'p': 'E(23456,78901,21222,41516)',    # performed (predicate)
    'o': 'E(34567,89012,31323,51617)'     # login (object)
  },
  {
    's': 'E(12345,67890,11121,31415)',    # alice (subject)
    'p': 'E(45678,90123,41424,61718)',    # timestamp (predicate)
    'o': 'E(56789,01234,51525,71819)'     # 2024-06-01T12:00:00Z (object)
  }
]

# Ready for cidstore insertion via ZMQ/msgpack
ctx = zmq.Context()
sock = ctx.socket(zmq.REQ)
sock.connect('tcp://cidstore:5555')

msg = {'command': 'batch_insert', 'triples': triples}
sock.send(msgpack.packb(msg, use_bin_type=True))
resp = msgpack.unpackb(sock.recv(), raw=False)
# Response: {"status": "ok", "inserted": 2, "version": "1.0"}
```

How to read this repo
- Each spec file is modular: high-level architecture, data models (machine-friendly JSON schemas), component responsibilities, API contracts, security/privacy rules, and operational guidance.
```
