## Label format enforcement

Ontology predicate entries MUST use a fully-qualified label/content with
exactly two colons before the human-readable label portion: `kind:namespace:label`.
The `kind` and `namespace` components may be empty (e.g. `::justLabel`) but
the two-colon separator form is REQUIRED — there must always be exactly two
colons present. Everything after the second
colon is treated as raw UTF-8 and is the human label (it may contain colons
and may begin with a colon). Examples:

- `E:usr:joined` => label `joined`
- `R:sys::startsWithColon` => kind: R (Relationship/Predicate), namespace: sys (core), label: `:startsWithColon` (leading colon preserved)
- `foo::bar:baz` => potentially malformed, misinterpreted as `foo` kind, empty namespace, `bar:baz` label
- `foo:bar` => malformed, missing second colon
- `foo` => malformed, missing colons
- `::justLabel` => potentially OK as special case, missing kind and namespace

The loader performs strict validation and will fail-fast on invalid entries.

## Term grammar

The system uses a small, consistent grammar for term namespaces.

- Entities: `E:<namespace>:<label>`
	- Examples: `E:usr:alice`, `E:geo:berlin`, `E:obj:cup123`

- Relations: `R:<namespace>:<label>`
	- Examples: `R:sys:madeClaimAbout`, `R:sys:livesIn`, `R:usr:friendsWith`

- Events: `EV:<namespace>:<label>`
	- Examples: `EV:usr:postedMessage`, `EV:sys:crashed`

- Literals: `L:<type>:<value>` (may be inline for small values or stored as a hashed reference for large blobs)
	- Examples: `L:int:42`, `L:str:"hello"`, `L:time:2025-10-05T17:00:00Z`

- Contexts / Rules: `C:<namespace>:<label>`
	- Example: `C:sys:CupPlacementRule`

All of the above follow the same fully-qualified pattern used for predicates (non-empty kind and namespace, human label is everything after the second colon and may contain colons).

## Ontology Growth Discipline

The ontology should remain deliberately constrained in size. New predicates (verbs/relations) MAY only be added when justified by measurable performance gains through specialized data structures or query optimization, NOT simply because they are semantically useful or convenient. This constraint is critical for maintaining performant OSP (Object-Subject-Predicate) lookups where queries enumerate all predicates. An unbounded ontology degrades query performance linearly with predicate count, whereas a compact ontology with specialized indexing structures enables fast retrieval. When considering a new predicate, the default answer is NO unless it enables concrete algorithmic improvements (e.g., dedicated spatial indexes for location predicates, temporal indexes for time-bound predicates, or specialized graph structures for hierarchical relationships).