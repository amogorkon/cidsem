from cidsem.wal import WAL


def test_wal_append_and_read(tmp_path):
    p = tmp_path / "testwal" / "wal.log"
    wal = WAL(str(p))
    r1 = {"id": 1, "idempotency_key": "abc", "payload": {"x": 1}}
    r2 = {"id": 2, "idempotency_key": "def", "payload": {"x": 2}}
    wal.append(r1)
    wal.append(r2)

    entries = list(wal.read_all())
    assert len(entries) == 2
    assert entries[0]["id"] == 1
    found = wal.find_by_idempotency_key("abc")
    assert found is not None and found["id"] == 1


def test_wal_replay(tmp_path):
    p = tmp_path / "testwal2" / "wal.log"
    wal = WAL(str(p))
    r1 = {"id": 3, "payload": {"x": 3}}
    wal.append(r1)
    seen = []

    def handler(rec):
        seen.append(rec["id"])

    wal.replay(handler)
    assert seen == [3]
