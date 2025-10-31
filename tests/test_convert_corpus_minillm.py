import json
from pathlib import Path

from cidsem.convert_corpus_with_minillm import convert_corpus


def test_convert_corpus_creates_triplets(tmp_path: Path):
    sample = {
        "items": [
            {
                "id": "doc1",
                "text": "Alice joined Acme Corp.",
                "expected": [{"id": "f1", "text": "Alice joined Acme Corp."}],
            }
        ]
    }
    infile = tmp_path / "in.json"
    outfile = tmp_path / "out.json"
    infile.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")

    convert_corpus(infile, outfile)

    data = json.loads(outfile.read_text(encoding="utf-8"))
    assert "items" in data
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert "triplets" in item
    assert len(item["triplets"]) == 1
    t = item["triplets"][0]
    # basic fields present
    assert t["id"] == "f1"
    assert "predicate_phrase" in t
    assert "predicate_fq" in t
    assert "predicate_cid" in t
    assert "subject" in t and "object" in t
