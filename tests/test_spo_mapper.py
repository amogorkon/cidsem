from cidsem.nlp.mapper import map_predicate
from cidsem.nlp.spo import extract_spo


def test_simple_extraction_and_map():
    s = "John joined Acme as CTO in 2019 after moving to San Francisco."
    triples = extract_spo(s)
    assert triples, "expected at least one SPO triple"
    subj, pred, obj = triples[0]
    assert subj == "john"
    # predicate should be something like 'joined'
    mapped = map_predicate(pred)
    assert mapped is not None
    assert "predicate" in mapped
    assert mapped["predicate"]["label"] in ("joined", "works as", "located at")


def test_no_verb_returns_empty():
    s = "QWERTY ZXCVB 1234"
    assert extract_spo(s) == []
