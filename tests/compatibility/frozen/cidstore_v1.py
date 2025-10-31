class TripleRecord:
    def __init__(
        self, subject, predicate, object, provenance=None, schema_version: str = "v1"
    ):
        self.subject = subject
        self.predicate = predicate
        self.object = object
        self.provenance = provenance or {}
        self.schema_version = schema_version

    def to_dict(self):
        return {}

    @classmethod
    def from_dict(cls, data):
        return cls(None, None, None)


class CidstoreClient:
    def __init__(self, cidstore_impl):
        self.cidstore = cidstore_impl

    def insert_triple(self, triple):
        return True

    def batch_insert_triples(self, triples):
        return {"success_count": len(triples), "failures": []}

    def query_by_subject_predicate(self, subject, predicate):
        return []

    def query_predicates_for_subject(self, subject):
        return []

    def query_subjects_by_object_predicate(self, obj, predicate):
        return []
