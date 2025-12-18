# Ontology

## Inverse Pair Documentation

**Storage and Query Architecture:**

CIDStore's inverse metadata system (`register_inverse(A, B)`) declares bidirectional inverse relationships between predicates. When both predicates in an inverse pair are registered as separate data structures (e.g., `owns` and `ownerOf`):

- **Storage**: Each triple is stored twice (once per predicate with SPO/OSP/POS indices)
- **Query routing**: Inverse queries on predicate A automatically route to predicate B's SPO index for efficient lookup
- **Alternative**: For predicates with multivalue stores, OSP indices already enable inverse queries without separate predicates, but routing through the inverse predicate's SPO index is faster

**Implementation**: The inverse registry maps predicate CIDs bidirectionally (`inverse_predicates: Dict[E, E]`) and provides query routing via `get_inverse(predicate)`.

## Meta-Predicates

Meta-predicates describe transformational relationships between predicates, enabling query transformation and reasoning.

| ID  | Short Name      | Description                                                                | Usage Type       |
|-----|-----------------|----------------------------------------------------------------------------|------------------|
| 001 | inverseOf       | Predicate A is inverse of B (swaps S↔O)                                    | Transformational |
| 002 | equivalentTo    | Predicates have identical semantics                                        | Transformational |
| 003 | implies         | Logical implication (can cross domains)                                    | Inferential      |

**Implementation Status:** These predicates are defined in the ontology vocabulary but CIDStore does not yet interpret them at runtime. The inverse registry uses code-based registration (`register_inverse(A, B)`) rather than data-driven `inverseOf` triples. Applications can store meta-predicate triples and implement their own reasoning logic.

**Example Usage:**
- `(R:social:childOf, inverseOf, R:social:parentOf)` - document inverse relationship
- `(R:social:married, equivalentTo, R:social:spouse)` - declare equivalence

## Logic

Boolean logic operators for predicate relationships. These define truth-value relationships between predicates.

| ID  | Short Name      | Description                                                                |
|-----|-----------------|----------------------------------------------------------------------------|
| 004 | or              | At least one predicate must be true: A ∨ B                                 |
| 005 | xor             | Exactly one predicate must be true: (A ∨ B) ∧ ¬(A ∧ B)                     |
| 006 | nand            | Predicates cannot both be true: ¬(A ∧ B)                                   |
| 007 | negates         | Predicate truth values are complements: P2(A,B) ≡ ¬P1(A,B)                 |

**Example Usage:**
- `(R:contact:email, or, R:contact:phone)` - at least one required
- `(R:status:alive, xor, R:status:dead)` - exactly one must be true
- `(R:role:employee, nand, R:role:contractor)` - can't be both at same company
- `(R:status:alive, negates, R:status:dead)` - complementary truth values (absence of one implies the other)

## Schema & Constraints

Schema predicates define type constraints for predicates.

| ID  | Short Name      | Description                                                                |
|-----|-----------------|----------------------------------------------------------------------------|
| 008 | hasDomain       | Predicate requires subject to be of specified type                         |
| 009 | hasRange        | Predicate requires object to be of specified type                          |

**Example Usage:**
- `(R:social:worksAt, hasDomain, E:type:Person)` - subject must be Person
- `(R:social:worksAt, hasRange, E:type:Organization)` - object must be Organization

## Predicate Properties Vocabulary (Markers)

Predicate properties are stored as ordinary SPO triples where the *predicate position* is a property-marker predicate. The existence of the triple indicates the property holds for the predicate subject.

To keep this evolvable, the property-marker predicates themselves are first-class entities that can be discovered at runtime (rather than hard-coded). We do that by typing them via the Type System (e.g., `isA PredicateProperty`).

| PV-ID | Property      | Description                                                     |
|-------|---------------|-----------------------------------------------------------------|
| PV-001| transitive    | P(A,B) ∧ P(B,C) ⇒ P(A,C)                                        |
| PV-002| symmetric     | P(A,B) ⇒ P(B,A)                                                 |
| PV-003| asymmetric    | P(A,B) ⇒ ¬P(B,A)                                               |
| PV-004| reflexive     | P(A,A) is always true                                           |
| PV-005| irreflexive   | P(A,A) is always false                                          |
| PV-006| composedOf    | P derived by path composition over other predicates             |

Storage pattern (marker triples):

- Declare which PV predicates are predicate-properties:
	- `(PV:transitive, isA, E:type:PredicateProperty)`
	- `(PV:symmetric, isA, E:type:PredicateProperty)`
	- `(PV:irreflexive, isA, E:type:PredicateProperty)`
	- `(PV:composedOf, isA, E:type:PredicateProperty)`

- Apply properties to predicates (marker triples):
	- `(R:family:ancestor, PV:transitive, E:meta:marker)`
	- `(R:social:married, PV:symmetric, E:meta:marker)`
	- `(R:family:childOf, PV:irreflexive, E:meta:marker)`
	- `(R:family:grandparent, PV:composedOf, [parentOf, parentOf])`

Lookup semantics:
- Discover property types (iterate all possible predicate-properties): query `(?prop, isA, E:type:PredicateProperty)`.
- Check whether predicate `P` has property `prop`: existence-check `(P, prop, E:meta:marker)`.
- For `composedOf`, the object encodes an ordered path of predicates used to materialize or answer derived queries.

Examples:
- Ancestor transitivity: given `(Alice, ancestor, Bob)` and `(Bob, ancestor, Carol)`, and marker `(ancestor, PV:transitive, _)`, infer `(Alice, ancestor, Carol)`.
- Married symmetry: if `(Bob, married, Alice)` exists and marker `(married, PV:symmetric, _)` is present, queries for `(?, married, Bob)` should return `Alice`.
- ChildOf irreflexivity: reject or flag attempts to insert `(Alice, childOf, Alice)` when `(childOf, PV:irreflexive, _)` exists.
- Grandparent composition: with `(grandparent, PV:composedOf, [parentOf, parentOf])`, answering `(Alice, grandparent, ?)` should follow the two-step path via `parentOf`.

### Design rationale

- Existence-first: CIDStore is optimized for existence checks; property markers leverage the fastest primitive.
- First-class predicates: treating predicates as entities aligns with the ontology’s bootstrapping model; properties attach via triples.
- Minimal coupling: property *types* are data (`isA PredicateProperty`), so clients can discover and adapt at runtime.
- Version stability: using a separate PV namespace avoids ID collisions and renumbering of core predicates.

### Why NOT entity property markers?

Unlike predicate properties (which describe *intrinsic mathematical properties* of relationships), common entity attributes like "verified", "active", or "public" are domain concepts better expressed through semantic predicates from the existing ontology:

- **Verification**: Use `(Entity, wasVerifiedBy, Agent)` + `(Entity, verifiedAt, Timestamp)` rather than boolean marker. Captures WHO verified and WHEN.
- **Lifecycle**: Use `(Entity, hasStatus, E:status:active)` or `(Entity, expiresAt, Timestamp)` rather than temporal marker. Supports state transitions with timestamps.
- **Deprecation**: Use `(Entity, deprecatedInFavorOf, NewEntity)` + `(Entity, deprecatedAt, Timestamp)` rather than boolean marker. Captures migration path and timing.
- **Access control**: Use `(Entity, visibleTo, Group)` or `(Entity, hasPermission, Permission)` rather than public/private markers. Enables fine-grained authorization.

This approach:
- Preserves semantic richness (WHO, WHEN, WHY, WHAT relationships)
- Avoids ontology pollution with domain-specific marker vocabularies
- Leverages existing predicates from Agency, Temporal, Social, and Structural domains
- Reserves marker pattern exclusively for meta-properties affecting reasoning (transitivity, symmetry, composition)

Entity "properties" are really just relationships to typed objects - use regular predicates.

### Custom marker vocabularies

For domain-specific needs where fast boolean checks are genuinely required and semantic predicates are insufficient, you can create custom marker vocabularies. Three object patterns are possible:

#### Option 1: Self-referential `(X, Marker, Marker)`

```
Declaration: (MyDomain:fastFlag, isA, E:type:Marker)
Application: (E:node:node42, MyDomain:fastFlag, MyDomain:fastFlag)
```

**Pros:**
- Visually distinctive - `(X, Foo, Foo)` signals "this is a marker"
- Self-contained - only two entities needed (X and Marker)
- Unambiguous intent at triple level

**Cons:**
- Cannot discover ALL marked entities without knowing marker names upfront
- No OSP clustering - each marker type has unique objects
- Semantically odd - "X is related to Foo via Foo"
- Requires knowing specific marker to query: `(?, MyMarker, MyMarker)`

#### Option 2: Shared sentinel `(X, Marker, E:meta:marker)`

```
Declaration: (MyDomain:fastFlag, isA, E:type:Marker)
Application: (E:node:node42, MyDomain:fastFlag, E:meta:marker)
```

**Pros:**
- Consistent with predicate properties pattern: `(ancestorOf, PV:transitive, E:meta:marker)`
- OSP clustering on single object - query `(?, ?, E:meta:marker)` finds ALL marked entities
- Clear separation between declaration and application
- Semantically clear - "X has Marker flag"

**Cons:**
- Requires separate sentinel entity `E:meta:marker`
- Less visually distinctive than self-reference
- Object doesn't identify WHICH marker (but predicate does)

#### Option 3: Type as object `(X, Marker, E:type:Marker)`

```
Declaration: (MyDomain:fastFlag, isA, E:type:Marker)
Application: (E:node:node42, MyDomain:fastFlag, E:type:Marker)
```

**Pros:**
- Maximum OSP clustering - query `(?, ?, E:type:Marker)` finds ALL marked entities
- No additional sentinel needed beyond the type entity
- Self-documenting - object says "this is a marker"
- Consistent with typed relationships

**Cons:**
- Semantic overload: `E:type:Marker` means "marker type category" in declarations AND "marked" in applications
- Potential confusion: `(Foo, isA, E:type:Marker)` vs `(X, Foo, E:type:Marker)` both use same object
- Less clear that object is just a flag vs a meaningful relationship

#### Recommendation

Use **Option 2** (`E:meta:marker` sentinel) for consistency with predicate properties and to maximize discovery via `(?, ?, E:meta:marker)`. This pattern:
- Maintains uniform marker infrastructure across predicate-properties and custom markers
- Enables "show me ALL marked entities" queries via OSP index
- Keeps semantic clarity (marker vs type-declaration)

**Declare marker type:**
```
(MyDomain:fastFlag, isA, E:type:Marker)
```

**Apply to entities:**
```
(E:node:node42, MyDomain:fastFlag, E:meta:marker)
```

**Query patterns:**
- Discover markers: `(?marker, isA, E:type:Marker)` - enumerates all marker types
- Check specific: `(entity, MyDomain:fastFlag, E:meta:marker)` - O(1) existence check
- Find all flagged by marker: `(?, MyDomain:fastFlag, E:meta:marker)` - O(1) OSP index lookup
- Find ALL marked entities: `(?, ?, E:meta:marker)` - O(p) fan-out across p marker predicates

**Performance characteristics:**

The shared sentinel `E:meta:marker` enables powerful introspection via `(?, ?, E:meta:marker)`, but this query scales with the number of marker predicates and flagged entities:

| Query Type | Complexity | Use Case | Hot Path? |
|------------|-----------|----------|-----------|
| `(entity, marker, E:meta:marker)` | O(1) | Boolean flag check | ✓ Yes |
| `(?, marker, E:meta:marker)` | O(n) | Find all entities with specific marker | ✓ Yes |
| `(?, ?, E:meta:marker)` | O(p×n) | Introspection: show ALL markers | ✗ No |

The `(?, ?, E:meta:marker)` query fans out to all marker predicates in parallel (via `query_osp_parallel`), collecting results from each. This is powerful for debugging and cleanup ("show me everything marked"), but should not be in hot paths.

**Empirical benchmark results (50k entities, 2 markers):**

Benchmarked on Rust CIDStore with real CID data (December 2025):

| Operation | Median Latency | Notes |
|-----------|---------------|-------|
| `has_marker(entity, marker)` | **61ns** | Optimized: skips value comparison for sentinel |
| Single marker query (50k entities) | **239ns** | Fan-out to all entities with one marker |
| Intersection (50k dataset) | **655ns** | Constant time! Independent of dataset size |
| Union (50k entities) | **1.76μs** | HashSet union for two marker sets |
| Difference (50k entities) | **604ns** | Constant time difference operation |
| Fan-out to all markers | **207ns** | O(p) scan across p=2 marker predicates |

**Key findings:**
- **61ns marker check** makes markers viable for hot-path boolean flags (vs ~30ns for raw HashMap<E, bool>)
- **Constant-time set operations** regardless of dataset size (655ns for 10k and 50k datasets!)
- **Iterative filtering dominates** for sparse conditions (10% deleted, 20% stale cache): ~800ns vs 2.4μs for set operations
- **Database comparison**: Redis GET is 1000-10,000× slower (~50-200μs); SQLite ~200-1600× slower (~10-100μs)

**Query strategy guidance (empirical):**

For complex marker queries like "find non-deleted entities with stale caches":

```rust
// Iterative filter approach: ~800ns for 10k entities (10% deleted, 20% stale)
for (entity, _) in store.query_all_o(sentinel) {
    if store.has_marker(entity, deleted) { continue; }  // Early exit optimization
    if store.has_marker(entity, stale) {
        results.push(entity);
    }
}

// Set operations approach: ~2.4μs (fixed overhead from HashSet allocation)
let type_set = query_and_collect(type_x, sentinel);
let deleted_set = query_and_collect(deleted, sentinel);
let stale_set = query_and_collect(stale, sentinel);
let result = type_set.difference(&deleted_set).filter(|e| stale_set.contains(e));
```

**Recommendation**: Default to iterative filtering with early exits (~800ns). Only materialize sets for:
- Very dense filtering (>50% matches)
- Reusing same sets multiple times
- Complex boolean logic clearer with set algebra

At 61ns per check, iterative filtering beats set operations' allocation overhead in typical sparse-condition scenarios.

**Filtering and composition (Rust + HDF5 storage):**

At the storage layer, CIDStore uses composite key rotation for efficient triple queries:

```rust
// Individual marker check (hot path) - O(1)
let has_flag = store.contains(entity, fastFlag, E_META_MARKER);

// Single marker query via (?, P, O) pattern - O(1) composite key lookup
let fast_entities = store.query_po(fastFlag, E_META_MARKER);  // Returns Vec<E>

// Set operations in Rust using HashSet
let fast_set: HashSet<E> = fast_entities.into_iter().collect();
let critical_set: HashSet<E> = store.query_po(criticalPath, E_META_MARKER).into_iter().collect();

// Intersection (entities with BOTH markers)
let both: HashSet<E> = fast_set.intersection(&critical_set).copied().collect();  // O(min(n1, n2))

// Union (entities with EITHER marker)
let either: HashSet<E> = fast_set.union(&critical_set).copied().collect();  // O(n1 + n2)

// Difference (fast but NOT critical)
let only_fast: HashSet<E> = fast_set.difference(&critical_set).copied().collect();  // O(n1)
```

**Fan-out to all marker types:**

```rust
// query_all_o(E:meta:marker) - finds ALL marked entities across ALL marker predicates
// Iterates known predicates (O(p)) and checks (?, predicate, E:meta:marker) via composite keys
let all_marked = store.query_all_o(E_META_MARKER);  // Vec<(subject, predicate)>

// Group by subject: "what markers does entity X have?"
let mut markers_by_entity: HashMap<E, Vec<E>> = HashMap::new();
for (subject, predicate) in all_marked {
    markers_by_entity.entry(subject).or_insert_with(Vec::new).push(predicate);
}
```

**Storage mechanics (composite key rotation):**

Each marker triple `(Entity, Marker, E:meta:marker)` creates index entries via key composition:
- **Rotation 0**: `compose(Entity, Marker, 0) → E:meta:marker` for (S, P, ?) lookup
- **Rotation 1**: `compose(Marker, E:meta:marker, 1) → Entity` for (?, P, O) lookup ← **This is the OSP index**
- **Rotation 2**: `compose(Entity, E:meta:marker, 2) → Marker` for (S, ?, O) lookup

The rotation-1 key is what makes `query_po(Marker, E:meta:marker)` O(1) - it's a direct HashMap lookup of a composed key, not a scan.

**Performance summary:**
- **Check if entity has marker**: O(1) via rotation-0 composed key lookup
- **Find all entities with specific marker**: O(1) via rotation-1 key lookup, returns Vec<E>
- **Find all markers on specific entity**: O(p) scan predicates, check rotation-2 keys
- **Set operations**: Standard Rust `HashSet` intersection/union/difference after materializing Vec<E>
- **Fan-out to ALL markers**: O(p) where p = number of known marker predicates, each is O(1) lookup

The composite key approach means marker queries don't need separate indices in HDF5 - the rotation parameter creates distinct keys from the same (A, B) pairs. The shared `E:meta:marker` object enables both targeted queries (when you know the marker) and global introspection (when you need all marked entities).

**When to use custom markers:**
- Hot-path filtering requiring maximum performance (millions of checks/sec)
- Binary flags with no semantic richness needed (WHO/WHEN/WHY don't matter)
- Algorithm internals (graph traversal flags, visited nodes, cache keys)

**When NOT to use custom markers:**
- Common domain attributes → use semantic predicates instead
- Anything that answers WHO/WHEN/WHY/WHAT → use relationships with typed objects
- Shared vocabularies → extend core ontology with proper predicates

Custom markers trade semantic expressiveness for query performance. Use sparingly.

Trade-offs and alternatives:
- Boolean triples: `(pred, isTransitive, true)` are explicit but introduce value parsing, truthy variants, and drift.
- Registry-only config: fast but opaque; not portable across stores and harder to reason over.
- Object-only tagging: `(pred, hasProperty, transitive)` is workable, but then `hasProperty` becomes yet another evolving predicate; with marker predicates + `isA PredicateProperty`, we keep existence checks and runtime enumeration without adding a dedicated property predicate.

Assumptions and cautions:
- Negation-based inference (e.g., via `negates`) requires a closed-world assumption or scoped completeness; absence alone does not imply false in open-world settings.
- Path composition representation SHOULD be canonical (ordered, namespace-qualified) to ensure deterministic query planning.

## Type System

Type system predicates define type hierarchies and instance-type relationships.

| ID  | Short Name      | Description                                                                |
|-----|-----------------|----------------------------------------------------------------------------|
| 010 | specializes     | Type to supertype (e.g., SeniorEngineer specializes Engineer)              |
| 011 | isA             | Instance to type relationship (e.g., Alice isA Person)                     |
| 012 | subClassOf      | Type specialization (synonym for specializes)                              |
| 013 | instanceOf      | Instance of type (synonym for isA)                                         |
| 014 | sameAs          | Identifiers denote same entity                                             |
| 015 | partOf          | General part-whole relationship                                            |

**Example Usage:**
- `(E:type:SeniorEngineer, specializes, E:type:Engineer)` - type hierarchy
- `(E:person:Alice, isA, E:type:SeniorEngineer)` - instance to type
- Can infer: `(E:person:Alice, isA, E:type:Engineer)` via transitivity
- Future: `(E:type:Engineer, generalizes, E:type:SeniorEngineer)` as inverse of specializes

## Core Predicates

### Social

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 015 | posted            | User posted message (system; symbolic)                |
| 016 | mentions          | Mentions entity/concept                               |
| 017 | states            | Assertive factual claim (S states O)                  |
| 018 | believes          | Expresses belief/opinion about O                      |
| 019 | asksAbout         | Question/asks about O                                 |
| 020 | cites             | References external source (URL, paper)               |
| 021 | joined            | Joined/started membership/role                        |
| 022 | left              | Left/ended membership/role                            |
| 023 | worksAt           | Employment relationship                               |
| 024 | livesIn           | Location/habitation                                   |
| 025 | hasEvent          | Event mention (time-scoped)                           |
| 026 | madeClaimAbout    | General claim relation (catch-all)                    |
| 027 | disagreesWith     | Contradiction/negation relation                       |
| 028 | supports          | Supports/endorses another claim or actor              |
| 029 | supportedBy       | Inverse of supports                                   |
| 030 | securityAlert     | Flagged content for security/moderation               |
| 031 | follows           | Social graph follows                                  |
| 032 | followedBy        | Inverse of follows                                    |
| 033 | likes             | Lightweight positive interaction                      |
| 034 | reactsTo          | Emoji/reaction engagement                             |
| 035 | bookmarks         | Saves message/entity for later                        |
| 036 | blocks            | Prevents another user from interacting                |
| 037 | mutes             | Hides content from another user                       |
| 038 | relationshipType  | Type of relationship (adoptive, biological, etc.)     |
| 039 | contradicts       | Information contradicts another assertion             |
| 040 | childOf           | Child of parent (biological, adoptive, etc.)          |
| 041 | parentOf          | Parent of child (biological, adoptive, etc.)          |
| 042 | hasSex            | Sex or gender identity                                |

### Social Knowledge

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 043 | knows             | Agent knows fact/agent                                |
| 044 | knownBy           | Inverse of knows                                      |
| 045 | influences        | Entity influences another                             |
| 046 | influencedBy      | Inverse of influences                                 |

### Identity & Ownership

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 047 | owns              | Entity owns an asset                                  |
| 048 | ownerOf           | Inverse of owns                                       |
| 049 | identifiedBy      | Entity mapped to identifier (email, DID, UUID)        |
| 050 | hasIdentifier     | General link to identifiers                           |
| 051 | ownsTitleTo       | Owns title/rights                                     |

### Lifecycle & Provenance

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 052 | createdBy         | Created by actor                                      |
| 053 | createdAt         | Creation timestamp                                    |
| 054 | modifiedBy        | Modified by actor                                     |
| 055 | modifiedAt        | Modification timestamp                                |
| 056 | deletedAt         | Deletion timestamp                                    |
| 057 | archived          | Marked as archived                                    |
| 058 | revoked           | Revoked access/permission                             |
| 059 | deprecated        | Marked as deprecated                                  |
| 060 | authorOf          | Authored content                                      |
| 061 | editorOf          | Edited content                                        |
| 062 | curatorOf         | Curated content                                       |
| 063 | signedBy          | Cryptographic signature reference                     |
| 064 | provenanceChain   | Multi-step provenance                                 |
| 065 | derivedVia        | Derived via transformation                            |
| 066 | supersedes        | Newer information replaces older assertion            |
| 067 | source            | Source of information (document, person, system)      |
| 068 | evidence          | Supporting evidence for assertion                     |

### Structural Modeling

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 069 | hasAttribute      | Entity has a property or field                        |
| 070 | hasMethod         | Entity has an operation/function                      |
| 071 | hasParameter      | Method/function parameter                             |
| 072 | associatedWith    | General association                                   |
| 073 | composedOf        | Strong whole-part relationship                        |
| 074 | hasPart           | Inverse of composedOf                                 |
| 075 | aggregatedOf      | Weaker whole-part relationship                        |
| 076 | implements        | Class realizes interface                              |
| 077 | implementedBy     | Inverse of implements                                 |
| 078 | hasCardinality    | Relationship cardinality                              |
| 079 | dependsOn         | Requires another element                              |
| 080 | requiredBy        | Inverse of dependsOn                                  |
| 081 | deployedOn        | Artifact deployed to environment                      |

### Behavioral

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 082 | calls             | Invokes another method                                |
| 083 | calledBy          | Inverse of calls                                      |
| 084 | triggers          | Causes transition/action                              |
| 085 | transitionsTo     | State changes to another                              |
| 086 | sendsMessage      | Sends message/signal                                  |
| 087 | hasGuardCondition | Condition guarding transition                         |
| 088 | inputs            | Action consumes data                                  |
| 089 | outputs           | Action produces data                                  |
| 090 | precedes          | Occurs before another                                 |

### Temporal

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 091 | occursAt          | Event occurs at time                                  |
| 092 | hasStartTime      | Event start time                                      |
| 093 | hasEndTime        | Event end time                                        |
| 094 | hasDuration       | Event/process duration                                |
| 095 | before            | Event before another                                  |
| 096 | after             | Event after another                                   |
| 097 | during            | Occurs within another                                 |
| 098 | overlapsWith      | Temporal overlap                                      |
| 099 | hasRecurrence     | Recurrence pattern                                    |
| 100 | hasTimestamp      | Timestamp of claim/post                               |
| 101 | effectiveFrom     | When this information becomes valid                   |
| 102 | effectiveUntil    | When this information expires                         |

### Spatial

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 103 | locatedAt         | Entity at specific location                           |
| 104 | hasCoordinates    | Lat/long coordinates                                  |
| 105 | within            | Contained within                                      |
| 106 | contains          | Contains entity                                       |
| 107 | adjacentTo        | Next to/bordering                                     |
| 108 | near              | Nearby                                                |
| 109 | hasAddress        | Postal/civic address                                  |
| 110 | hasPath           | Spatial path                                          |
| 111 | origin            | Starting point                                        |
| 112 | destination       | End point                                             |
| 113 | direction         | Orientation                                           |

### Spatiotemporal

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 114 | trajectory        | Spatial path over time                                |
| 115 | velocity          | Speed and direction                                   |
| 116 | movementFromTo    | Movement event                                        |
| 117 | occupies          | Presence at location/time                             |

### Agency

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 118 | isProcess         | Entity is an ongoing process                          |
| 119 | hasProcess        | Involves a process                                    |
| 120 | participatesIn    | Actor participates in process                         |
| 121 | initiates         | Agent starts process                                  |
| 122 | terminates        | Agent ends process                                    |
| 123 | intendsTo         | Intention                                             |
| 124 | attempts          | Attempt (may fail)                                    |
| 125 | causes            | Causes event                                          |
| 126 | causedBy          | Caused by                                             |
| 127 | resultedIn        | Result of event                                       |
| 128 | enables           | Condition enables                                     |
| 129 | prevents          | Condition prevents                                    |
| 130 | responsibleAgent  | Accountable participant                               |
| 131 | hasGoal           | Entity has purpose                                    |
| 132 | achieves          | Action achieves goal                                  |

### Uncertainty

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 133 | likelyTrue        | High probability                                      |
| 134 | possibly          | Possibly true                                         |
| 135 | necessarily       | Must be true                                          |
| 136 | hasProbability    | Numerical probability                                 |
| 137 | hasConfidence     | Confidence level                                      |
| 138 | hasUncertainty    | Uncertainty measure                                   |
| 139 | errorMargin       | Measurement error margin                              |
| 140 | confidenceInterval| Statistical confidence interval                       |
| 141 | measurementMethod | How measured                                          |
| 142 | confidence        | Confidence level (0.0-1.0)                            |
| 143 | certaintyType     | Type of uncertainty (random, systematic, etc.)        |

### Physical

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 144 | hasMass           | Physical mass                                         |
| 145 | hasVolume         | Physical volume                                       |
| 146 | hasColor          | Physical color                                        |
| 147 | hasTemperature    | Temperature                                           |
| 148 | hasMaterial       | Material composition                                  |
| 149 | hasState          | Physical state (solid/liquid/gas)                     |

### Data

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 150 | hasValue          | Literal value                                         |
| 151 | hasUnit           | Unit of measure                                       |
| 152 | hasDataType       | Literal data type                                     |
| 153 | minValue          | Minimum value                                         |
| 154 | maxValue          | Maximum value                                         |
| 155 | hasPrecision      | Numerical precision                                   |
| 156 | hasHash           | Hash of content                                       |
| 157 | contentAddressedBy| CID or hash pointer                                   |
| 158 | canonicalizedAs   | Canonical form                                        |
| 159 | hashAlgorithm     | Hash algorithm used                                   |
| 160 | canonicalizationMethod | Method of canonicalization                       |

### Security

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 161 | verifiedBy        | Verified by source/method                             |
| 162 | trusts            | Agent trusts entity                                   |
| 163 | hasProvenance     | Has provenance                                        |
| 164 | hasIntegrity      | Integrity check                                       |
| 165 | hasAuthorization  | Permission/authorization                              |
| 166 | accessLevel       | Access level (public, private, restricted)            |
| 167 | visibility        | Visibility setting                                    |
| 168 | consentGiven      | Consent provided                                      |
| 169 | consentRevoked    | Consent revoked                                       |
| 170 | redacted          | Content redacted                                      |
| 171 | masked            | Content masked                                        |
| 172 | licenseUnder      | Licensing of content                                  |
| 173 | termsOfUse        | Usage terms                                           |
| 174 | compliesWith      | Complies with policy                                  |
| 175 | violatesPolicy    | Violates policy                                       |

### Metadata

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 176 | taggedWith        | Tagged with keyword                                   |
| 177 | annotatedBy       | Annotated by actor                                    |
| 178 | confidenceSource  | Source of confidence score                            |
| 179 | languageOf        | Language of literal                                   |
| 180 | localizedAs       | Localized representation                              |
| 181 | contextOf         | Discourse or context                                  |
| 182 | withinContext     | Occurs within context                                 |

### Transactions

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 183 | transfers         | Transfer of ownership/value                           |
| 184 | paidBy            | Paid by agent                                         |
| 185 | priceOf           | Price of entity                                       |

### Legal

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 186 | legalBasis        | Legal foundation (court order, contract, etc.)        |

### Context

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 187 | context           | Context where this assertion applies                  |

### Logical

| ID  | Short Name        | Description                                           |
|-----|-------------------|-------------------------------------------------------|
| 188 | assumption        | Underlying assumption made                            |

## Registered Inverse Pairs

The following predicate pairs are registered as inverses in CIDStore's inverse registry:

| Forward Predicate | ID  | Inverse Predicate | ID  | Domain          |
|-------------------|-----|-------------------|-----|-----------------|
| follows           | 031 | followedBy        | 032 | Social          |
| owns              | 047 | ownerOf           | 048 | Ownership       |
| childOf           | 040 | parentOf          | 041 | Social          |
| contains          | 106 | within            | 105 | Spatial         |
| before            | 095 | after             | 096 | Temporal        |
| causes            | 125 | causedBy          | 126 | Causal          |
| composedOf        | 073 | hasPart           | 074 | Structural      |
| dependsOn         | 079 | requiredBy        | 080 | Structural      |
| calls             | 082 | calledBy          | 083 | Behavioral      |
| implements        | 076 | implementedBy     | 077 | Structural      |
| supports          | 028 | supportedBy       | 029 | Social          |
| influences        | 045 | influencedBy      | 046 | Social          |
| knows             | 043 | knownBy           | 044 | Social          |

## Label Format Enforcement

Label format enforcement: Labels SHOULD follow the canonical short-name style used in this ontology (camelCase or PascalCase where appropriate). Systems integrating with this ontology are encouraged to validate predicate labels for conformity during ingestion to ensure interoperability.

Example canonical label form (namespace-qualified):

	kind:namespace:label

For example: kind:person:parentOf or kind:org:worksAt

Grammar terms:

- Entities: `E:<namespace>:<label>`
- Relations: `R:<namespace>:<label>`
- Events: `EV:<namespace>:<label>`
- Literals: `L:<type>:<value>`

Notes:

- Short-form labels may still be used in some contexts, e.g. `::justLabel` for local-only labels.
- Labels may be accompanied by a content-address (sha1/sha256) or a human-readable description for provenance and matching purposes.
