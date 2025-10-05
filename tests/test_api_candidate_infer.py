import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")
from cidsem.api.app import app
from cidsem.wal import WAL

client = TestClient(app)


def make_payload_without_candidates():
    return {
        "factoid_id": "f-infer-1",
        "factoid_text": "Alice joined BetaCorp as CTO in 2020.",
        "provenance": {"msg_cid": "bafy", "chunk_id": "c-1"},
    }


def test_infer_predicates_and_persist(tmp_path, monkeypatch):
    walp = tmp_path / "wal_infer.log"
    monkeypatch.setenv("CIDSEM_WAL", str(walp))
    payload = make_payload_without_candidates()
    r = client.post("/candidate_factoids", json=payload)
    assert r.status_code == 200
    # read WAL and confirm predicate_candidates were injected
    w = WAL(str(walp))
    records = list(w.read_all())
    assert records, "expected records in WAL"
    rec = records[-1]
    assert rec["type"] == "candidate_factoid"
    p = rec["payload"].get("predicate_candidates")
    assert p and isinstance(p, list)
    # expect at least one mapped predicate cid
    assert any("predicate_cid" in x for x in p)
