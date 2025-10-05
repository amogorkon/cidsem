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
# CIDSEM — Introduction

This repository defines the CIDSEM specification: a content-addressed semantic extraction and curation platform that converts text streams into auditable RDF-like triples recorded in a content-addressable store (CIDStore). The system is organized around two complementary extraction paths:

- Real-time symbolic extraction: deterministic, low-latency rules and pattern matchers that can auto-assert high-confidence triples.
- Dreaming batch pipeline: higher-latency LLM-based extraction + coreference that produces curated candidate triples and helps evolve the predicate registry and models.

Between these paths sits the Validation Layer: a human-and-bot mediated loop that prevents low-confidence LLM outputs from polluting the canonical graph while producing high-quality labeled data for retraining.

Goals
- Deterministic, content-addressed artifacts (CIDs) for traceability and deduplication.
- Clear machine-readable schemas for all artifacts (chunk, factoid, triple, validation event, backlog item, predicate entry).
- Strong provenance and auditability: every asserted triple links back to the originating message, factoid, and validation event(s).
- Safe rollout via a validation loop and pilot predicates to minimize harm from hallucination or PII exposure.

Audience and intent
- This spec is a living design for engineers building the ingestion, extraction, validation, and insertion pipeline; product/UX for curator flows; and ML teams that consume labeled events for retraining.

How to read this repo
- Each spec file is modular: high-level architecture, data models (machine-friendly JSON schemas), component responsibilities, API contracts, security/privacy rules, and operational guidance.
```
