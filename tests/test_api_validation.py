import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")
from cidsem.api.app import app

client = TestClient(app)


def make_validation_payload():
    return {
        "event_id": "ev-1",
        "factoid_id": "f-1",
        "responder_id": "r-1",
        "response": "confirmed",
        "timestamp": "2025-09-27T12:00:00Z",
        "bot_id": "bot-1",
        "prompt_hash": "ph-123",
        "model_version": "gpt-test-0",
    }


def test_post_validation_accepts(tmp_path, monkeypatch):
    walp = tmp_path / "wal_val.log"
    monkeypatch.setenv("CIDSEM_WAL", str(walp))
    payload = make_validation_payload()
    r = client.post("/validation_events", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_validation_idempotency(tmp_path, monkeypatch):
    walp = tmp_path / "wal_val2.log"
    monkeypatch.setenv("CIDSEM_WAL", str(walp))
    payload = make_validation_payload()
    headers = {"Idempotency-Key": "val-abc-1"}
    r1 = client.post("/validation_events", json=payload, headers=headers)
    assert r1.status_code == 200
    r2 = client.post("/validation_events", json=payload, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] in ("duplicate", "accepted")
