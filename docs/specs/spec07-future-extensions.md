# 9. Benefits & Optional Enhancements

## 9. Benefits
✅ Deterministic: CIDs guarantee consistent addressing across all nodes.
✅ Performant: SIMD-friendly fixed-width encoding, batch hashing.
✅ Distributed & Dynamic: Schema evolution is decentralized and safe.
✅ Extensible: Handlers can be written, registered, and hot-deployed.
✅ Self-Describing: System contains its own schema ontology, encoded as content.

## 10. Optional Enhancements
🔐 Signed schemas and handler verification.
🧠 Schema introspection and inference (e.g., schema similarity).
📦 WASM-dispatch modules for portable, safe execution.
🔄 Versioning and upgrade semantics between schema generations.
 
## Pilot plan & next steps

The following actions should be completed during an initial pilot (small scope) to validate the proposed architecture and the Validation Layer.

1. Machine-readable schemas (high priority)
	- Add strict JSON Schema files for `CandidateFactoid` and `ValidationEvent` (already done). Add `TripleRecord`, `Chunk`, `BacklogItem`, and `PredicateRegistryEntry` schemas next.

2. Pilot predicates and scope
	- Start with 1–2 high-value predicates (e.g., `t:joined`, `t:worksAt`) and a small user subset or closed test group.

3. Minimal pilot implementation
	- Hook micro-LLM fallback to `POST /candidate_factoids`.
	- Implement a simple Bot Service (Barkeep persona) to post prompts and collect one-click responses.
	- Validation Worker enforces TTL and consensus rules and calls CIDStore insert on confirmation (staging CIDStore).

4. Observability & datasets
	- Dashboard: prompts posted, responses, resolution latency, expired rate.
	- Create a gold dataset (200–500 annotated messages) for the pilot predicates.

5. Safety & privacy
	- Preprocessor redaction and opt-out for pinging users.
	- Moderator lane for PII and high-impact factoids.

6. Evaluation & iterate
	- Run shadow testing, calibrate thresholds, collect labeled examples for retraining.

Note: treat top-level proposed changes (`spec98`, `spec99`) as reference appendices; pilots and implementation should use them as guidance but keep the canonical spec files under `spec00`..`spec08` as the main implementation-spec.
