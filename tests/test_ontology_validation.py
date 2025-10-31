import json

from cidsem.nlp import mapper


def write_ont(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)


def test_load_ontology_accepts_leading_colon_label(tmp_path, monkeypatch):
    # prepare a minimal ontology with a content that has a leading colon
    ont = {
        "comment": "test",
        "predicates": [
            {"cid": 1, "content": "R:sys::startsWithColon", "description": "test"}
        ],
    }
    f = tmp_path / "ontology.json"
    write_ont(f, ont)

    # point mapper to the temp file
    monkeypatch.setattr(mapper, "ONTO_FILE", str(f))

    loaded = mapper.load_ontology()
    assert "predicates" in loaded
    # mapping should work and preserve the leading colon in human label
    mapped = mapper.map_predicate("startsWithColon")
    assert mapped is not None
    pred = mapped["predicate"]
    assert pred.get("label") == ":startsWithColon"


def test_load_ontology_rejects_bad_label(tmp_path, monkeypatch):
    # missing two colons -> invalid
    ont = {"predicates": [{"cid": 2, "content": "badlabel", "description": "x"}]}
    f = tmp_path / "ontology.json"
    write_ont(f, ont)
    monkeypatch.setattr(mapper, "ONTO_FILE", str(f))

    try:
        mapper.load_ontology()
        assert False, "expected ValueError for bad label"
    except ValueError as e:
        assert "missing fully-qualified label" in str(e)
