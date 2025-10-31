import json

from cidsem.nlp import mapper


def write_ont(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)


def test_split_exact_three_parts_with_extra_colons(tmp_path, monkeypatch):
    # two entries: one simple, one with extra colon(s) in the human label
    ont = {
        "predicates": [
            {"cid": 1, "content": "a:b:c", "description": "simple"},
            {"cid": 2, "content": "a:b:c:d", "description": "extra"},
        ]
    }
    f = tmp_path / "ontology.json"
    write_ont(f, ont)
    monkeypatch.setattr(mapper, "ONTO_FILE", str(f))

    loaded = mapper.load_ontology()
    preds = loaded.get("predicates", [])
    assert len(preds) == 2

    # check split behavior: exactly three parts and human label preserved including extra colons
    for p, expected_label in zip(preds, ["c", "c:d"]):
        full = p.get("label") or p.get("content")
        parts = full.split(":", 2)
        assert len(parts) == 3
        assert parts[2] == expected_label


def test_load_ontology_rejects_missing_second_colon(tmp_path, monkeypatch):
    ont = {"predicates": [{"cid": 3, "content": "foo:bar", "description": "bad"}]}
    f = tmp_path / "ontology.json"
    write_ont(f, ont)
    monkeypatch.setattr(mapper, "ONTO_FILE", str(f))

    try:
        mapper.load_ontology()
        assert False, "expected ValueError for missing second colon"
    except ValueError as e:
        assert "two colons" in str(e) or "fully-qualified" in str(e)
