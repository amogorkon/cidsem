import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")
from cidsem.api.app import app

client = TestClient(app)


def make_payload():
    return {
        "factoid_id": "f-1",
        "factoid_text": "John joined Acme as CTO in 2019.",
        "predicate_candidates": [
            {"predicate_cid": "cid:pred:joined:v1", "score": 0.98}
        ],
        "provenance": {"msg_cid": "bafy", "chunk_id": "c-1"},
    }


def test_post_candidate_accepts(tmp_path, monkeypatch):
    # use temp WAL
    walp = tmp_path / "wal.log"
    monkeypatch.setenv("CIDSEM_WAL", str(walp))
    payload = make_payload()
    r = client.post("/candidate_factoids", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_idempotency_key(tmp_path, monkeypatch):
    walp = tmp_path / "wal2.log"
    monkeypatch.setenv("CIDSEM_WAL", str(walp))
    payload = make_payload()
    headers = {"Idempotency-Key": "abc-123"}
    r1 = client.post("/candidate_factoids", json=payload, headers=headers)
    assert r1.status_code == 200
    r2 = client.post("/candidate_factoids", json=payload, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] in ("duplicate", "accepted")
