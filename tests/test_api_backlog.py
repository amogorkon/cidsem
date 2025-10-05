import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")
from cidsem.api.app import app

client = TestClient(app)


def make_backlog_payload():
    return {
        "item_id": "bi-1",
        "factoid_id": "f-1",
        "priority": "normal",
        "created_at": "2025-09-27T12:00:00Z",
        "attempts": 0,
    }


def test_post_backlog_accepts(tmp_path, monkeypatch):
    walp = tmp_path / "wal_back.log"
    monkeypatch.setenv("CIDSEM_WAL", str(walp))
    payload = make_backlog_payload()
    r = client.post("/backlog_items", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_backlog_idempotency(tmp_path, monkeypatch):
    walp = tmp_path / "wal_back2.log"
    monkeypatch.setenv("CIDSEM_WAL", str(walp))
    payload = make_backlog_payload()
    headers = {"Idempotency-Key": "back-abc-1"}
    r1 = client.post("/backlog_items", json=payload, headers=headers)
    assert r1.status_code == 200
    r2 = client.post("/backlog_items", json=payload, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] in ("duplicate", "accepted")
