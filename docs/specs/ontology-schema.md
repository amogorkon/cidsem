# Ontology JSON Schema

## Overview
The canonical ontology.json defines the **173 base predicates** (explicit inverse predicates removed in favor of `inverseOf` metadata) with full metadata required for schema generation, dispatcher routing, and query planning. This document specifies the JSON structure and field definitions.

## Schema Structure

```json
{
  "$schema": "ontology/v1",
  "version": "1.0.0",
  "generated_at": "2025-12-15T00:00:00Z",
  "namespace": "R",
  "predicates": [
    {
      "id": 1,
      "kind": "R",
      "namespace": "social",
      "label": "posted",
      "cid": "sha256:abc123...",
      "description": "user posted message (system; symbolic)",
      "category": "Social",
      "domain": {
        "type": "entity",
        "description": "User or agent posting"
      },
      "range": {
        "type": "entity",
        "description": "Posted message or content"
      },
      "cardinality": "single",
      "temporal": false,
      "spatial": false,
      "sortable": false,
      "reversible": false,
      "inverse_of": null,
      "metadata": {
        "canonical_label": "R:social:posted",
        "short_form": "posted",
        "aliases": [],
        "notes": "System predicate; symbolic only"
      }
    },
    {
      "id": 16,
      "kind": "R",
      "namespace": "social",
      "label": "follows",
      "cid": "sha256:def456...",
      "description": "social graph follows relationship",
      "category": "Social",
      "domain": {
        "type": "entity",
        "description": "Actor (user, agent, entity)"
      },
      "range": {
        "type": "entity",
        "description": "Followed entity"
      },
      "cardinality": "multi",
      "temporal": false,
      "spatial": false,
      "sortable": false,
      "reversible": true,
      "inverse_of": null,
      "metadata": {
        "canonical_label": "R:social:follows",
        "short_form": "follows",
        "aliases": ["follows_entity"],
        "notes": "inverseOf: R:social:followedBy (explicit inverse removed in base set)",
        "optimization": "Base set keeps forward predicate only; inverse satisfied via inverseOf metadata"
      }
    }
  ],
  "inverse_pairs": [],
  "missing_inverses": [
    {
      "predicate_id": 50,
      "predicate_label": "R:structural:composedOf",
      "suggested_inverse": "R:structural:composingOf",
      "rationale": "Whole-part relationship; candidate for future expansion"
    }
  ],
  "duplicate_candidates": [
    {
      "predicate_ids": [142, 157],
      "predicate_label": "verifiedBy",
      "issue": "Same short name but different descriptions/scopes",
      "resolution": "Clarify with namespace: R:security:verifiedBy vs R:metadata:verifiedBy"
    }
  ]
}
```

## Layering: Base vs CIDSEM Expansion

- **Base (cidstore)**: Minimal, authoritative predicate set (**target 173 after applying inverseOf meta-optimization: drop explicit inverses 17, 26, 77, 86, 107, 179**). Contains only the metadata required for routing: domain/range, cardinality, temporal/spatial/sortable flags, reversible/inverseOf hints.
- **Expansion (cidsem)**: Namespaced enrichments (semantics, aliases, validation rules, ontology links). These do **not** change routing; they inform planning and validation.
- **Caching**: cidstore may cache cidsem expansion data at startup or via a refresh endpoint. Cached expansions are used for query planning hints (inverseOf, disambiguation, validation), while dispatch continues to rely solely on base metadata.
- **Identifier discipline**: Queries use predicate CIDs. If an expansion is present, cidstore augments planning with the expansion but keeps dispatch decisions bound to the base definition.

## Field Definitions

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `$schema` | string | yes | Schema identifier: `ontology/v1` |
| `version` | string | yes | Ontology version (semver) |
| `generated_at` | ISO 8601 | yes | Generation timestamp |
| `namespace` | string | yes | Default namespace prefix (typically `R` for relations) |
| `predicates` | array | yes | Array of predicate objects |
| `inverse_pairs` | array | no | Documented inverse relationships (for optimization tracking) |
| `missing_inverses` | array | no | Candidate inverses for future addition |
| `duplicate_candidates` | array | no | Predicates requiring namespace clarification |

### Predicate Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | yes | Unique predicate ID (1-179 in spec23; base set uses 173 after removing explicit inverses) |
| `kind` | string | yes | Predicate kind: `R` (relation), `E` (entity), `L` (literal), `EV` (event) |
| `namespace` | string | yes | Namespace qualifier (e.g., `social`, `temporal`, `security`) |
| `label` | string | yes | Short label without kind/namespace (e.g., `follows`, `posted`) |
| `cid` | string | yes | Content ID (SHA256 hash of canonical label) |
| `description` | string | yes | Human-readable description |
| `category` | string | yes | Category from spec23 (e.g., `Social`, `Temporal`, `Security`) |
| `domain` | object | yes | Type(s) that can be subject (S) |
| `range` | object | yes | Type(s) that can be object (O) |
| `cardinality` | string | yes | `single` (direct) or `multi` (CardinalityStore dispatch) |
| `temporal` | boolean | yes | Has timestamp component (→ TemporalStore) |
| `spatial` | boolean | yes | Has coordinate component (→ SpatialStore) |
| `sortable` | boolean | yes | Can be ordered (e.g., by value, timestamp) |
| `reversible` | boolean | yes | Has an inverse relationship (captured via `inverseOf` metadata). Base set keeps forward predicate; inverse may be absent as explicit predicate. |
| `inverse_of` | integer \| null | yes | Optional pointer to explicit inverse if present. In base set (173), this is typically null; use metadata.inverse_label to document inverse name. |
| `metadata` | object | yes | Additional metadata (see below) |

### Domain/Range Objects

```json
{
  "type": "entity|literal|any",
  "description": "Description of valid values",
  "entity_type_restriction": "optional constraint (e.g., Person, Organization)",
  "literal_type": "optional (e.g., integer, string, timestamp for literals)"
}
```

### Metadata Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `canonical_label` | string | yes | Full qualified label `kind:namespace:label` |
| `short_form` | string | yes | Short form used in some contexts (camelCase) |
| `aliases` | array | no | Alternative names for this predicate |
| `notes` | string | no | Implementation notes, warnings, or hints |
| `optimization` | string | no | Optimization opportunities (e.g., use inverseOf instead of explicit) |
| `inverse_label` | string | no | Name of the inverse predicate when the explicit inverse is omitted from the base set (e.g., `R:social:followedBy`). |

## CID Generation

CID (Content ID) for each predicate is computed as:

```
cid = "sha256:" + hex(sha256(canonical_label))

Example:
  canonical_label = "R:social:follows"
  cid = "sha256:a1b2c3d4e5f6..." (first 32 chars of sha256 hash)
```

Use `sha2` crate in Rust:
```rust
use sha2::{Sha256, Digest};

fn generate_cid(canonical_label: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(canonical_label.as_bytes());
    let hash = hasher.finalize();
    format!("sha256:{}", hex::encode(&hash[..]))
}
```

## Validation Rules (spec20 compliance)

1. **Label format**: `kind:namespace:label` where:
   - `kind` ∈ {R, E, L, EV} (one of these)
   - `namespace` = lowercase alphanumeric (e.g., `social`, `temporal`, `security`)
   - `label` = camelCase or PascalCase (e.g., `follows`, `Posted`, `hasType`)

2. **Uniqueness**:
   - No two predicates with same `kind:namespace:label` (canonical label is unique)
   - CIDs must be distinct (follows from unique canonical labels)
   - Short names may collide across namespaces (e.g., `verifiedBy` in security vs metadata), but canonical labels won't

3. **Namespace discipline**:
   - Use existing namespaces where appropriate (social, temporal, security, spatial, etc.)
   - Create new namespace only if predicate truly belongs to separate semantic domain
   - Document new namespaces in top-level `namespace_registry` field

4. **Cardinality annotation**:
   - `single`: Direct (S, P) → O lookup; dispatch to CompositeStore
   - `multi`: Multi-valued (S, P) → [O, O, ...]; dispatch to CardinalityStore with sentinel

5. **Inverse tracking**:
   - If `reversible: true`, must have `inverse_of: <id>` pointing to inverse predicate
   - Inverse predicate must also have `reversible: true` and `inverse_of: <original_id>` (bidirectional)

6. **Temporal/Spatial/Sortable flags**:
   - Set `temporal: true` if range is timestamp (dispatch to TemporalStore)
   - Set `spatial: true` if range is coordinates (dispatch to SpatialStore)
   - Set `sortable: true` if values have natural ordering (enables range queries)

## Optimization Annotations

### Inverse Pair Optimization

```json
{
  "id": 16,
  "label": "follows",
  "reversible": true,
  "inverse_of": 17,
  "metadata": {
    "optimization": "Currently has explicit inverse (followedBy, id 17). Can optimize by merging into single predicate with inverseOf metadata. Reduces predicate count from 179 → 150. Improves POS query performance by ~40% (fewer predicates to scan)."
  }
}
```

### Missing Inverse Annotation

```json
{
  "id": 50,
  "label": "composedOf",
  "reversible": false,
  "inverse_of": null,
  "metadata": {
    "notes": "Inverse (composingOf) not currently defined. Candidate for future expansion if queries require reverse composition lookup."
  }
}
```

### Duplicate Disambiguation

```json
{
  "id": 142,
  "label": "verifiedBy",
  "namespace": "security",
  "description": "verified by source/method",
  "metadata": {
    "notes": "WARNING: Duplicate short name with id 157. Canonical label R:security:verifiedBy disambiguates. See also id 157 for R:metadata:verifiedBy."
  }
}
```

## Example: Minimal Valid Ontology Fragment

```json
{
  "$schema": "ontology/v1",
  "version": "1.0.0",
  "generated_at": "2025-12-15T00:00:00Z",
  "namespace": "R",
  "predicates": [
    {
      "id": 1,
      "kind": "R",
      "namespace": "social",
      "label": "posted",
      "cid": "sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
      "description": "user posted message",
      "category": "Social",
      "domain": {"type": "entity", "description": "User"},
      "range": {"type": "entity", "description": "Message"},
      "cardinality": "single",
      "temporal": false,
      "spatial": false,
      "sortable": false,
      "reversible": false,
      "inverse_of": null,
      "metadata": {
        "canonical_label": "R:social:posted",
        "short_form": "posted",
        "aliases": []
      }
    }
  ],
  "inverse_pairs": [],
  "missing_inverses": [],
  "duplicate_candidates": []
}
```

## Migration Path: spec23 → ontology.json

1. For each row in spec23 table:
   - Extract ID, short name, description, category
   - Infer namespace from category (Social → social, Temporal → temporal, etc.)
   - Compute canonical label: `R:{namespace}:{shortname}`
   - Generate CID via SHA256
   - Infer cardinality from description (e.g., "multiple" → multi, default → single)
   - Set temporal/spatial/sortable based on semantic meaning

2. For each inverse pair identified in spec23:
   - Create two predicate entries with `reversible: true`
   - Link via `inverse_of` field
   - Annotate optimization opportunity

3. Validate entire file against schema:
   - No duplicate canonical labels
   - All inverse pairs bidirectional
   - All required fields present
   - CIDs correctly computed

4. Example row transformation:

   **spec23**:
   ```
   | 16 | follows | social graph follows | Social |
   | 17 | followedBy | inverse of follows | Social |
   ```

   **ontology.json** (two entries):
   ```json
   {
     "id": 16,
     "kind": "R",
     "namespace": "social",
     "label": "follows",
     "cid": "sha256:...",
     "description": "social graph follows relationship",
     "category": "Social",
     "domain": {"type": "entity", "description": "Actor"},
     "range": {"type": "entity", "description": "Followed entity"},
     "cardinality": "multi",
     "temporal": false,
     "spatial": false,
     "sortable": false,
     "reversible": true,
     "inverse_of": 17,
     "metadata": {
       "canonical_label": "R:social:follows",
       "short_form": "follows",
       "optimization": "Can merge with followedBy using inverseOf metadata"
     }
   },
   {
     "id": 17,
     "kind": "R",
     "namespace": "social",
     "label": "followedBy",
     "cid": "sha256:...",
     "description": "inverse of follows (who follows this entity)",
     "category": "Social",
     "domain": {"type": "entity", "description": "Followed entity"},
     "range": {"type": "entity", "description": "Follower"},
     "cardinality": "multi",
     "temporal": false,
     "spatial": false,
     "sortable": false,
     "reversible": true,
     "inverse_of": 16,
     "metadata": {
       "canonical_label": "R:social:followedBy",
       "short_form": "followedBy",
       "optimization": "Candidate for removal; use inverseOf on follows (id 16) instead"
     }
   }
   ```

## Tools & Utilities

### Validation Script
```python
# Python script to validate ontology.json against schema
# Check: unique labels, bidirectional inverses, valid CIDs, required fields

import json
import hashlib

def generate_cid(canonical_label: str) -> str:
    h = hashlib.sha256(canonical_label.encode()).hexdigest()
    return f"sha256:{h[:40]}"  # Truncate for readability

def validate_ontology(path: str):
    with open(path) as f:
        onto = json.load(f)

    errors = []

    # Check unique canonical labels
    labels = [p['metadata']['canonical_label'] for p in onto['predicates']]
    if len(labels) != len(set(labels)):
        errors.append("Duplicate canonical labels found")

    # Check bidirectional inverses
    for p in onto['predicates']:
        if p['reversible'] and p['inverse_of'] is not None:
            inv = next((x for x in onto['predicates'] if x['id'] == p['inverse_of']), None)
            if not inv or inv['inverse_of'] != p['id']:
                errors.append(f"Predicate {p['id']} has broken inverse relationship")

    # Check CID correctness
    for p in onto['predicates']:
        expected_cid = generate_cid(p['metadata']['canonical_label'])
        if p['cid'] != expected_cid:
            errors.append(f"Predicate {p['id']} has incorrect CID")

    return errors

if __name__ == '__main__':
    errors = validate_ontology('ontology.json')
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
    else:
        print("✓ Ontology validation passed")
```

## Next Steps

1. **Generate full ontology.json**:
   - Expand from 15 → 179 predicates
   - Fill in all metadata fields
   - Compute CIDs for all predicates
   - Validate against this schema

2. **Integrate with CIDStore dispatcher**:
   - Load ontology.json on startup
   - Wire predicate metadata → dispatch routing
   - Use CIDs as predicate references in queries

3. **Update CIDSEM query planner**:
   - Use CIDs instead of short names
   - Leverage metadata for optimization (inverseOf, cardinality, etc.)
   - Plan queries based on predicate properties

4. **Document integration examples**:
   - Show how to query by predicate CID
   - Explain dispatch routing (direct vs sentinel vs specialized)
   - Provide examples for each query pattern
