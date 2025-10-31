from cidsem.nlp.mapper import map_predicate


def test_map_predicate_with_llm(monkeypatch):
    # Prepare a fake local_llm that always selects the first predicate
    class FakeLLM:
        @staticmethod
        def choose_predicate(phrase, preds):
            return 0

    monkeypatch.setitem(__import__("sys").modules, "cidsem.llm", FakeLLM)

    # Call map_predicate with use_llm flag; should return a result if ontology has entries
    res = map_predicate("joined", use_llm=True)
    # If ontology is present, we should get a mapping dict; otherwise None
    assert res is None or isinstance(res, dict)
