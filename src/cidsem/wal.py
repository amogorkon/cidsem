import json
import os
from typing import Callable, Optional


class WAL:
    """Simple append-only WAL using JSON lines.

    Each record is a JSON object and will be appended with a newline.
    """

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # ensure file exists
        open(self.path, "a", encoding="utf-8").close()

    def append(self, record: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_all(self):
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    def find_by_idempotency_key(self, key: str) -> Optional[dict]:
        for rec in self.read_all():
            if rec.get("idempotency_key") == key:
                return rec
        return None

    def replay(self, handler: Callable[[dict], None]) -> None:
        for rec in self.read_all():
            handler(rec)
