import os

from cidsem.nlp import mapper


def test_spec23_contains_label_note():
    here = os.path.dirname(__file__)
    path = os.path.join(here, "..", "docs", "specs", "spec23-Ontology.md")
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    assert "Label format enforcement" in content
    assert "kind:namespace:label" in content
    # grammar terms
    assert "Entities: `E:<namespace>:<label>`" in content
    assert "Relations: `R:<namespace>:<label>`" in content
    assert "Events: `EV:<namespace>:<label>`" in content
    assert "Literals: `L:<type>:<value>`" in content
    # updated examples / notes
    assert "::justLabel" in content
    assert ("sha1" in content.lower()) or ("human-readable description" in content)


def test_ontology_file_conforms():
    # load_ontology performs strict validation and will raise ValueError on bad entries
    ont = mapper.load_ontology()
    assert "predicates" in ont
    for p in ont.get("predicates", []):
        full = p.get("label") or p.get("content") or ""
        parts = full.split(":", 2)
        # spec changed: require at least two colons (len(parts) >= 3);
        # empty kind/namespace may be allowed as a special case per the spec.
        assert full and len(parts) >= 3
        assert ("cid" in p) or isinstance(p.get("entity"), dict)
