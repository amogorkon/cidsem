"""Example: demonstrate cidsem pushing (SHA -> content) to Redis when inserting triples.

This script uses a MockCidstore implementation to avoid requiring a running cidstore service.
It demonstrates that CidstoreClient will write to Redis (if available) using the
`CIDSEM_USE_REDIS`, `REDIS_HOST`, and `REDIS_PORT` environment variables.

Usage:
    # ensure redis is running (e.g., docker compose from repo)
    pip install redis
    python scripts/redis_integration_example.py

If Redis is not available, the script will still show the cidstore insert flow but
will skip the Redis writes.
"""

# no external json dependency needed in this example

from cidsem.cidstore import CidstoreClient, TripleRecord
from cidsem.keys import E


class MockCidstore:
    def insert(self, key, value):
        print(f"MockCidstore.insert called: key={key}, value={value}")

    def batch_insert(self, batch):
        print(f"MockCidstore.batch_insert called: {len(batch)} items")


def make_sample_triple():
    subj = E.from_str("E(1,2,3,4)")
    pred = E.from_str("E(5,6,7,8)")
    obj = E.from_str("E(9,10,11,12)")
    tr = TripleRecord(subj, pred, obj, provenance={})
    # attach a fake hash to mimic computed triple_hash
    tr.provenance["triple_hash"] = "deadbeefcafebabe"
    return tr


def main():
    print("Starting example: will attempt to write to Redis if available...")
    mock = MockCidstore()
    client = CidstoreClient(mock)

    triple = make_sample_triple()

    ok = client.insert_triple(triple)
    print("insert_triple returned:", ok)

    # try to read back from redis if enabled
    if client.redis is not None:
        val = client.redis.get(triple.provenance["triple_hash"])
        if val:
            if isinstance(val, (bytes, bytearray)):
                print("Retrieved from Redis:", val.decode("utf-8"))
            else:
                print("Retrieved from Redis:", val)
        else:
            print("No value found in Redis for key", triple.provenance["triple_hash"])
    else:
        print("Redis not enabled or available; skipping verification.")


if __name__ == "__main__":
    main()
