import json
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs" / "specs" / "spec23-Ontology.md"
OUT_PATH = ROOT / "docs" / "specs" / "ontology.json"

drop_inverse_ids = {17, 26, 77, 86, 107, 179}

category_namespace = {
    "Social": "social",
    "Identity & Ownership": "identity",
    "Lifecycle & Provenance": "lifecycle",
    "Lifecycle": "lifecycle",
    "Structural Modeling": "structural",
    "Behavioral": "behavior",
    "Ontological": "ontological",
    "Temporal": "temporal",
    "Spatial": "spatial",
    "Spatiotemporal": "spatiotemporal",
    "Agency": "agency",
    "Uncertainty": "uncertainty",
    "Physical": "physical",
    "Data": "data",
    "Security": "security",
    "Metadata": "metadata",
    "Transactions": "transactions",
    "Social Knowledge": "social_knowledge",
    "Provenance": "provenance",
    "Legal": "legal",
    "Context": "context",
    "Logical": "logical",
}

multi_predicates = {
    # social relationships and tags
    "follows", "likes", "reactsTo", "bookmarks", "blocks", "mutes", "mentions", "supports", "disagreesWith", "asksAbout", "madeClaimAbout", "hasEvent",
    # identity/ownership
    "owns", "ownerOf", "worksAt", "livesIn", "relationshipType",
    # structural
    "hasAttribute", "hasMethod", "hasParameter", "hasCardinality", "dependsOn", "calls", "associatedWith", "composedOf", "aggregatedOf", "implements",
    # behavioral
    "triggers", "transitionsTo", "sendsMessage", "inputs", "outputs", "precedes",
    # temporal/spatial
    "overlapsWith", "hasRecurrence", "contains", "within", "hasPath", "adjacentTo", "near",
    # agency/causality
    "participatesIn", "initiates", "terminates", "causes", "resultedIn", "enables", "prevents", "achieves",
    # data/metadata
    "taggedWith", "annotatedBy", "hasValue", "hasUnit", "hasDataType",
    # security/provenance
    "verifiedBy", "trusts", "hasProvenance", "consentGiven", "consentRevoked", "masked", "redacted",
    # transactions
    "transfers", "paidBy", "priceOf",
    # knowledge
    "knows", "influences",
    # family
    "childOf", "parentOf",
}


def slug_namespace(category: str) -> str:
    return category_namespace.get(category.strip(), re.sub(r"[^a-z0-9]+", "_", category.strip().lower()).strip("_"))


def generate_cid(canonical_label: str) -> str:
    h = hashlib.sha256(canonical_label.encode()).hexdigest()
    return f"sha256:{h}"


def parse_spec23():
    text = SPEC_PATH.read_text(encoding="utf-8")
    rows = []
    pattern = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)
    for m in pattern.finditer(text):
        pid = int(m.group(1))
        if pid in drop_inverse_ids:
            continue
        short = m.group(2).strip()
        desc = m.group(3).strip()
        category = m.group(4).strip()
        rows.append((pid, short, desc, category))
    return rows


def build_predicate(pid: int, short: str, desc: str, category: str):
    namespace = slug_namespace(category)
    canonical_label = f"R:{namespace}:{short}"
    cid = generate_cid(canonical_label)
    temporal = category.lower() in {"temporal", "spatiotemporal"}
    spatial = category.lower() in {"spatial", "spatiotemporal"}
    sortable = temporal or spatial
    cardinality = "multi" if short in multi_predicates else "single"
    reversible = False
    inverse_of = None
    return {
        "id": pid,
        "kind": "R",
        "namespace": namespace,
        "label": short,
        "cid": cid,
        "description": desc,
        "category": category,
        "domain": {"type": "entity", "description": ""},
        "range": {"type": "entity", "description": ""},
        "cardinality": cardinality,
        "temporal": temporal,
        "spatial": spatial,
        "sortable": sortable,
        "reversible": reversible,
        "inverse_of": inverse_of,
        "metadata": {
            "canonical_label": canonical_label,
            "short_form": short,
            "aliases": [],
            "notes": ""
        }
    }


def main():
    rows = parse_spec23()
    predicates = [build_predicate(*row) for row in rows]
    doc = {
        "$schema": "ontology/v1",
        "version": "1.0.0",
        "generated_at": "2025-12-15T00:00:00Z",
        "namespace": "R",
        "predicates": predicates,
        "inverse_pairs": [],
        "missing_inverses": [],
        "duplicate_candidates": [
            {
                "predicate_ids": [142, 157],
                "predicate_label": "verifiedBy",
                "issue": "Same short name but different descriptions/scopes",
                "resolution": "Clarify with namespace: R:security:verifiedBy vs R:metadata:verifiedBy"
            }
        ]
    }
    OUT_PATH.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {len(predicates)} predicates to {OUT_PATH}")


if __name__ == "__main__":
    main()
