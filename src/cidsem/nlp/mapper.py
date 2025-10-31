import json
import json as _json
import os
import time
from difflib import SequenceMatcher
from functools import lru_cache

from cidsem.nlp.normalizer import normalize_predicate

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCHEMA_DIR = os.environ.get("CIDSEM_SCHEMA_DIR", os.path.join(ROOT, "docs", "spec"))
ONTO_FILE = os.path.join(SCHEMA_DIR, "ontology.json")


def load_ontology():
    try:
        ont = json.load(open(ONTO_FILE))
    except FileNotFoundError:
        return {"predicates": []}

    # Basic validation: each predicate should provide a fully-qualified
    # label/content with the form 'kind:namespace:label...' (at least two
    # ':' separators) and either a 'cid' or an 'entity' dict so callers can
    # obtain a stable identifier.
    preds = ont.get("predicates", []) or []
    for i, p in enumerate(preds):
        full_label = p.get("label") or p.get("content") or ""
        parts = full_label.split(":", 2)
        # require at least three parts (two colons). Empty kind/namespace are
        # allowed per the current spec; only ensure the two-separator form.
        if not full_label or len(parts) < 3:
            raise ValueError(
                f"ontology predicate at index {i} missing fully-qualified label/content (expected 'kind:namespace:label...' with two colons): {full_label!r}"
            )
        if "cid" not in p and not isinstance(p.get("entity"), dict):
            raise ValueError(
                f"ontology predicate at index {i} missing 'cid' or 'entity' identifier: {full_label!r}"
            )

    return ont


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def map_predicate(
    phrase: str, threshold: float = 0.6, use_llm: bool = False
) -> dict | None:
    """Map a predicate phrase to the best ontology predicate if above threshold.
    Returns the matching predicate dict or None.
    """
    ont = load_ontology()
    best = None
    best_score = 0.0
    # normalize phrase locally before matching
    norm = normalize_predicate(phrase)

    # If requested, attempt to let a local LLM pick among ontology candidates.
    if use_llm:
        try:
            # import here to avoid optional dependency at module import time
            from cidsem import llm

            choice = llm.choose_predicate(norm, ont.get("predicates", []))
            if choice is not None:
                if isinstance(choice, int):
                    idx = choice
                else:
                    # attempt to find the predicate dict in ontology list
                    try:
                        idx = ont.get("predicates", []).index(choice)
                    except ValueError:
                        idx = None
                if idx is not None:
                    chosen = ont.get("predicates", [])[idx]
                    result_pred = dict(chosen)
                    result_pred["label"] = (
                        result_pred.get("label") or result_pred.get("content") or ""
                    )
                    parts = result_pred["label"].split(":", 2)
                    result_pred["label"] = (
                        parts[2] if len(parts) == 3 else result_pred["label"]
                    )
                    return {"predicate": result_pred, "score": 1.0}
        except Exception:
            # fall back to fuzzy matching below
            pass
    for p in ont.get("predicates", []):
        # ontology labels are fully-qualified like 'kind:namespace:label...'
        # Per spec the first two ':' split kind and namespace; everything after
        # the second ':' is the human label (may contain colons). Extract that
        # portion for fuzzy matching. The ontology file may use either 'label'
        # or 'content' as the fully-qualified string, so accept both.
        full_label = p.get("label") or p.get("content") or ""
        parts = full_label.split(":", 2)
        human_label = parts[2] if len(parts) == 3 else full_label
        sc = _score(norm.lower(), human_label.lower())
        if sc > best_score:
            best_score = sc
            best = p
    if best_score >= threshold:
        # Return a copy of the matched predicate with a normalized human
        # 'label' field containing the extracted human_label so callers can
        # rely on p['label'] regardless of the original ontology field name.
        result_pred = dict(best)
        # ensure label key exists and is the human readable portion
        result_pred["label"] = (
            result_pred.get("label") or result_pred.get("content") or ""
        )
        parts = result_pred["label"].split(":", 2)
        result_pred["label"] = parts[2] if len(parts) == 3 else result_pred["label"]
        return {"predicate": result_pred, "score": best_score}
    return None


def map_predicate_candidates(
    phrase: str,
    subject: str | None = None,
    object: str | None = None,
    context: str | None = None,
    top_k: int = 3,
    use_llm: bool = False,
) -> list:
    """Return up to top_k candidate mappings for a predicate phrase.

    This is a deterministic, rule-first stub implementation used for
    testing and local development. It scores ontology entries using
    fuzzy string similarity on the human-readable label and returns
    CandidateMapping-like dicts with keys:
    - pred_id: stable identifier (cid or JSON-serialized entity)
    - score: float in [0,1]
    - label: human label
    - explanation: short text why chosen
    - backend: 'rules' or 'llm'
    - latency_ms: time taken to compute

    The function is intentionally deterministic and cached for repeated
    calls with the same normalized inputs.
    """

    start = time.time()

    # Prepare cache key components
    subj_k = subject or ""
    obj_k = object or ""
    ctx_k = context or ""

    @lru_cache(maxsize=4096)
    def _inner_cached(key_phrase, key_subj, key_obj, key_ctx, k, use_llm_flag):
        ont = load_ontology()
        norm = normalize_predicate(key_phrase)

        candidates = []

        # If use_llm is requested, try to ask the optional llm chooser for
        # a preferred ordering. This implementation will place the LLM's
        # single choice first (if any) and then fall back to fuzzy ranking.
        chosen_idx = None
        if use_llm_flag:
            try:
                from cidsem import llm

                choice = llm.choose_predicate(norm, ont.get("predicates", []))
                if choice is not None:
                    if isinstance(choice, int):
                        chosen_idx = choice
                    else:
                        try:
                            chosen_idx = ont.get("predicates", []).index(choice)
                        except ValueError:
                            chosen_idx = None
            except Exception:
                chosen_idx = None

        scored = []
        for idx, p in enumerate(ont.get("predicates", [])):
            full_label = p.get("label") or p.get("content") or ""
            parts = full_label.split(":", 2)
            human_label = parts[2] if len(parts) == 3 else full_label
            sc = _score(norm.lower(), human_label.lower())
            scored.append((idx, sc, p, human_label))

        # If an LLM chose an index, boost it to the top with score 1.0
        if chosen_idx is not None:
            for i, sc, p, human_label in scored:
                if i == chosen_idx:
                    scored = [(i, 1.0, p, human_label)] + [
                        s for s in scored if s[0] != i
                    ]
                    break

        # Sort by score desc, deterministic tie-break by index
        scored.sort(key=lambda x: (-x[1], x[0]))

        # Normalize scores to [0,1] relative to top score (avoid division by 0)
        if scored:
            top_score = scored[0][1]
            if top_score <= 0:
                top_score = 1.0
        else:
            top_score = 1.0

        for rank, (idx, sc, p, human_label) in enumerate(scored[:k]):
            # pred_id: prefer 'cid' if present, otherwise JSON-serialize entity
            pcid = p.get("cid")
            if pcid is None and isinstance(p.get("entity"), dict):
                try:
                    pcid = _json.dumps(p.get("entity"), sort_keys=True)
                except Exception:
                    pcid = str(p.get("entity"))
            if not isinstance(pcid, str):
                pcid = str(pcid)

            normalized_score = float(sc / top_score) if top_score else float(sc)

            candidates.append({
                "pred_id": pcid,
                "score": normalized_score,
                "label": human_label,
                "explanation": f"fuzzy-match:{sc:.3f}",
                "backend": "llm" if (use_llm_flag and idx == chosen_idx) else "rules",
            })

        latency_ms = (time.time() - start) * 1000.0
        # Attach latency to first candidate for visibility
        if candidates:
            candidates[0]["latency_ms"] = latency_ms

        return tuple(_json.dumps(c, sort_keys=True) for c in candidates)

    # Call cached inner function
    raw = _inner_cached(phrase, subj_k, obj_k, ctx_k, top_k, use_llm)
    # Convert back to dicts
    out = [_json.loads(x) for x in raw]
    return out
