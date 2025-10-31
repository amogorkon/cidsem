from cidsem import llm


class DummyModel:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, texts, convert_to_numpy=True):
        # deterministic small embeddings: length of text and first char code
        import numpy as _np

        out = []
        for t in texts:
            a = len(t)
            b = ord(t[0]) if t else 0
            out.append([a, b])
        return _np.array(out, dtype=float)


def test_choose_predicate_with_stub(monkeypatch):
    # patch SentenceTransformer in llm module
    monkeypatch.setattr("cidsem.llm.SentenceTransformer", DummyModel, raising=False)

    preds = [
        {"content": "R:sys:joined"},
        {"content": "R:org:hired"},
        {"content": "R:org:left"},
    ]
    idx = llm.choose_predicate("joined", preds)
    # should return an index (int) or None
    assert idx is None or isinstance(idx, int)
