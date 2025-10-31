from cidsem.cidstore import CidstoreClient, TripleRecord, create_compound_key
from cidsem.keys import E
from tests.conftest import InMemoryCidstore

s = E.from_str("Alice")
p = E.from_str("worksAt")
o = E.from_str("BetaCorp")
print("subject lanes:", s.high, s.high_mid, s.low_mid, s.low)
print("predicate lanes:", p.high, p.high_mid, p.low_mid, p.low)
print("object lanes:", o.high, o.high_mid, o.low_mid, o.low)

store = InMemoryCidstore()
client = CidstoreClient(store)
client.insert_triple(TripleRecord(s, p, o))
print("store keys:")
for k, v in store._store.items():
    print(k, v)

lookup_key = create_compound_key(s, p)
print(
    "lookup_key tuple:",
    (lookup_key.high, lookup_key.high_mid, lookup_key.low_mid, lookup_key.low),
)
print("normalized lookup:", store._norm(lookup_key))
print("lookup result:", store.lookup(lookup_key))
