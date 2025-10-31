"""
Test cidstore integration functionality.

Tests the E entity handling, triple insertion, and batch operations
as described in the cidsem specifications.
"""

from cidsem.cidstore import (
    CidstoreClient,
    PerformanceConfig,
    TripleRecord,
    create_compound_key,
    create_reverse_key,
    extract_context_to_triples,
    robust_batch_insert_with_retry,
)
from cidsem.keys import E


class TestEEntity:
    """Test E entity functionality."""

    def test_e_from_str(self):
        """Test deterministic E entity generation from strings."""
        e1 = E.from_str("Alice")
        e2 = E.from_str("Alice")
        e3 = E.from_str("Bob")

        assert e1 == e2  # Same string -> same E
        assert e1 != e3  # Different strings -> different E
        assert isinstance(e1, E)
        assert e1.high > 0 or e1.low > 0  # Non-zero entity

    def test_e_high_low_fields(self):
        """Test E entity high/low field access."""
        e = E.from_str("test_entity")

        assert isinstance(e.high, int)
        assert isinstance(e.low, int)
        assert 0 <= e.high < (1 << 64)
        assert 0 <= e.high_mid < (1 << 64)
        assert 0 <= e.low_mid < (1 << 64)
        assert 0 <= e.low < (1 << 64)

        # Reconstruct E from 4-part representation
        e2 = E((e.high, e.high_mid, e.low_mid, e.low))
        assert e == e2

    def test_e_serialization_format(self):
        """Test E entity msgpack serialization format."""
        e = E.from_str("serialization_test")

        # Test dict format with high/low fields
        e_dict = {
            "high": e.high,
            "high_mid": e.high_mid,
            "low_mid": e.low_mid,
            "low": e.low,
        }
        e_reconstructed = E((
            e_dict["high"],
            e_dict["high_mid"],
            e_dict["low_mid"],
            e_dict["low"],
        ))

        assert e == e_reconstructed


class TestTripleRecord:
    """Test TripleRecord functionality."""

    def test_triple_record_creation(self):
        """Test creating and serializing TripleRecord."""
        subject = E.from_str("Alice")
        predicate = E.from_str("worksAt")
        obj = E.from_str("BetaCorp")

        provenance = {"factoid_id": "f-1", "factoid_text": "Alice works at BetaCorp"}
        triple = TripleRecord(subject, predicate, obj, provenance)

        assert triple.subject == subject
        assert triple.predicate == predicate
        assert triple.object == obj
        assert triple.provenance == provenance
        assert triple.schema_version == "v1"
        assert triple.created_at > 0

    def test_triple_record_serialization(self):
        """Test TripleRecord to_dict/from_dict roundtrip."""
        subject = E.from_str("Alice")
        predicate = E.from_str("worksAt")
        obj = E.from_str("BetaCorp")

        triple = TripleRecord(subject, predicate, obj)
        triple_dict = triple.to_dict()

        # Check dict structure
        assert "subject" in triple_dict
        assert "predicate" in triple_dict
        assert "object" in triple_dict
        assert triple_dict["subject"]["high"] == subject.high
        assert triple_dict["subject"]["high_mid"] == subject.high_mid
        assert triple_dict["subject"]["low_mid"] == subject.low_mid
        assert triple_dict["subject"]["low"] == subject.low

        # Test roundtrip
        triple2 = TripleRecord.from_dict(triple_dict)
        assert triple2.subject == subject
        assert triple2.predicate == predicate
        assert triple2.object == obj


class TestCompoundKeys:
    """Test compound key generation for queries."""

    def test_compound_key_creation(self):
        """Test compound key generation is deterministic."""
        subject = E.from_str("Alice")
        predicate = E.from_str("worksAt")

        key1 = create_compound_key(subject, predicate)
        key2 = create_compound_key(subject, predicate)

        assert key1 == key2  # Deterministic
        assert isinstance(key1, E)

        # Different inputs should produce different keys
        predicate2 = E.from_str("livesIn")
        key3 = create_compound_key(subject, predicate2)
        assert key1 != key3

    def test_reverse_key_creation(self):
        """Test reverse key generation for object+predicate lookups."""
        predicate = E.from_str("worksAt")
        obj = E.from_str("BetaCorp")

        key1 = create_reverse_key(predicate, obj)
        key2 = create_reverse_key(predicate, obj)

        assert key1 == key2  # Deterministic
        assert isinstance(key1, E)


class TestCidstoreClient:
    """Test CidstoreClient operations."""

    def test_single_triple_insertion(self, cidstore_client):
        """Test inserting a single triple."""
        mock_cidstore = cidstore_client
        client = CidstoreClient(mock_cidstore)

        subject = E.from_str("Alice")
        predicate = E.from_str("worksAt")
        obj = E.from_str("BetaCorp")
        triple = TripleRecord(subject, predicate, obj)

        result = client.insert_triple(triple)
        assert result is True

        # Verify the compound key was stored
        compound_key = create_compound_key(subject, predicate)
        stored_objects = mock_cidstore.lookup(compound_key)
        assert len(stored_objects) > 0

    def test_batch_triple_insertion(self, cidstore_client):
        """Test batch insertion of multiple triples."""
        mock_cidstore = cidstore_client
        client = CidstoreClient(mock_cidstore)

        # Create test triples
        triples = []
        for i in range(3):
            subject = E.from_str(f"Person{i}")
            predicate = E.from_str("worksAt")
            obj = E.from_str(f"Company{i}")
            triple = TripleRecord(subject, predicate, obj)
            triples.append(triple)

        result = client.batch_insert_triples(triples)

        assert result["success_count"] == 3
        assert len(result["failures"]) == 0

    def test_query_by_subject_predicate(self, cidstore_client):
        """Test querying objects by subject+predicate."""
        mock_cidstore = cidstore_client
        client = CidstoreClient(mock_cidstore)

        # Insert a triple
        subject = E.from_str("Alice")
        predicate = E.from_str("worksAt")
        obj = E.from_str("BetaCorp")
        triple = TripleRecord(subject, predicate, obj)

        client.insert_triple(triple)

        # Query it back
        objects = client.query_by_subject_predicate(subject, predicate)
        assert len(objects) > 0
        # Note: The mock cidstore returns tuples, so we need to handle that
        found_obj = objects[0]
        if isinstance(found_obj, tuple):
            found_obj = E(found_obj)
        assert found_obj == obj

    def test_query_predicates_for_subject(self, cidstore_client):
        """Test finding all predicates for a subject."""
        mock_cidstore = cidstore_client
        client = CidstoreClient(mock_cidstore)

        subject = E.from_str("Alice")
        predicate1 = E.from_str("worksAt")
        predicate2 = E.from_str("livesIn")
        obj1 = E.from_str("BetaCorp")
        obj2 = E.from_str("Seattle")

        # Insert two triples with same subject
        client.insert_triple(TripleRecord(subject, predicate1, obj1))
        client.insert_triple(TripleRecord(subject, predicate2, obj2))

        # Query predicates
        predicates = client.query_predicates_for_subject(subject)
        assert len(predicates) >= 2  # Should have at least our 2 predicates


class TestContextExtraction:
    """Test context-to-triple extraction."""

    def test_extract_context_to_triples(self):
        """Test converting factoid context to TripleRecord objects."""
        factoid_text = "Alice joined BetaCorp as CTO in 2020."
        factoid_id = "f-test-1"
        predicate_candidates = [
            {
                "predicate_cid": '{"high": 2222222222222222222, "low": 3333333333333333333}',
                "score": 0.9,
                "label": "joined",
            }
        ]

        triples = extract_context_to_triples(
            factoid_text, factoid_id, predicate_candidates
        )

        assert len(triples) == 1
        triple = triples[0]

        assert isinstance(triple, TripleRecord)
        assert isinstance(triple.subject, E)
        assert isinstance(triple.predicate, E)
        assert isinstance(triple.object, E)
        assert triple.provenance["factoid_id"] == factoid_id
        assert triple.provenance["factoid_text"] == factoid_text


class TestPerformanceAndRetry:
    """Test performance optimization and retry logic."""

    def test_performance_config(self):
        """Test PerformanceConfig creation and defaults."""
        config = PerformanceConfig()

        assert config.target_throughput_ops_per_sec == 1_000_000
        assert config.target_latency_p99_microsec == 100
        assert config.adaptive_batch_size is True
        assert config.retry_max_attempts == 3

    def test_robust_batch_insert_success(self, cidstore_client):
        """Test robust batch insert with successful case."""
        mock_cidstore = cidstore_client
        client = CidstoreClient(mock_cidstore)

        # Create test triples
        triples = []
        for i in range(2):
            subject = E.from_str(f"TestPerson{i}")
            predicate = E.from_str("hasSkill")
            obj = E.from_str(f"Skill{i}")
            triple = TripleRecord(subject, predicate, obj)
            triples.append(triple)

        result = robust_batch_insert_with_retry(client, triples)

        assert result["success_count"] == 2
        assert len(result["failures"]) == 0


class TestCidstoreIntegration:
    """Integration tests combining multiple components."""

    def test_end_to_end_workflow(self, cidstore_client):
        """Test complete workflow: context -> triples -> cidstore -> query."""
        mock_cidstore = cidstore_client
        client = CidstoreClient(mock_cidstore)

        # Step 1: Extract triples from context
        factoid_text = "Alice works at BetaCorp."
        factoid_id = "f-integration-1"
        predicate_candidates = [
            {
                "predicate_cid": '{"high": 6666666666666666666, "low": 7777777777777777777}',
                "score": 0.95,
                "label": "worksAt",
            }
        ]

        triples = extract_context_to_triples(
            factoid_text, factoid_id, predicate_candidates
        )
        assert len(triples) == 1

        # Step 2: Insert into cidstore
        result = client.batch_insert_triples(triples)
        assert result["success_count"] == 1
        assert len(result["failures"]) == 0

        # Step 3: Query back the data
        triple = triples[0]
        objects = client.query_by_subject_predicate(triple.subject, triple.predicate)
        assert len(objects) > 0

        # Step 4: Query predicates for subject
        predicates = client.query_predicates_for_subject(triple.subject)
        assert len(predicates) > 0
