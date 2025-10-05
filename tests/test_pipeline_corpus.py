import json
import re

from cidsem.nlp.mapper import map_predicate
from cidsem.nlp.spo import extract_spo
from cidsem.utils.factoids import build_factoids


def test_corpus_pipeline_runs():
    data = json.load(open("tests/fixtures/corpus_texts.json"))
    items = data.get("items", [])
    assert items

    mapped_count = 0
    for it in items:
        text = it.get("text", "")
        triples = extract_spo(text)
        outputs = []
        for subj, pred, obj in triples:
            # normalize predicate locally
            mapped = map_predicate(pred)
            phrase = " ".join(filter(None, [subj, pred, obj])).strip()
            outputs.append(phrase)
            if mapped:
                mapped_count += 1
        # if expected provided, check it is subset of outputs
        expected = it.get("expected", [])
        for exp in expected:
            # support legacy string expectations and new dict form {id,text}
            if isinstance(exp, dict):
                exp_text = exp.get("text")
                exp_id = exp.get("id")
                # build factoids and ensure the expected id/text pair exists
                factoids = build_factoids(it.get("id"), text, triples)
                # allow expected text to be a substring of the produced factoid text
                assert any(
                    f.get("id") == exp_id and (exp_text or "") in (f.get("text") or "")
                    for f in factoids
                ), (
                    f"expected factoid {exp_id}:{exp_text} in produced factoids {factoids}"
                )
                # if exp_text is a normal factoid text (not a derived-id reference like 'X001F01 happened 2019'),
                # also assert it appears among extractor outputs
                if exp_text and not re.match(r"^X\d+F\d+", str(exp_text)):
                    assert any(exp_text in out for out in outputs), (
                        f"expected '{exp_text}' in outputs {outputs} for item {it.get('id')}"
                    )
            else:
                exp_text = exp
                assert any(exp_text in out for out in outputs), (
                    f"expected '{exp_text}' in outputs {outputs} for item {it.get('id')}"
                )
        # no explicit expected factoid ids — we validate against expected text only
    # expect at least 4 mappings in this small corpus
    assert mapped_count >= 4
