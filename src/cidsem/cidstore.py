"""
cidstore.py - Integration utilities for cidstore operations

Provides utilities for:
- Triple insertion with E entities
- Batch operations with msgpack serialization
- Compound key generation for subject-predicate-object queries
- Performance optimizations and error recovery
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from zvic import constrain_this_module

from .hashcache import get_triple_hash
from .keys import E

# Enable ZVIC runtime checks for cidstore module if not explicitly disabled.
try:
    if os.getenv("CIDSEM_ZVIC_ENABLED", "1") == "1":
        constrain_this_module()
except Exception:
    # Don't prevent import if ZVIC is misconfigured in the environment
    pass


class TripleRecord:
    """Represents a complete triple ready for cidstore insertion with provenance."""

    def __init__(
        self,
        subject: E,
        predicate: E,
        object: E,
        provenance: Optional[Dict[str, Any]] = None,
        schema_version: str = "v1",
    ):
        self.subject = subject
        self.predicate = predicate
        self.object = object
        self.provenance = provenance or {}
        self.schema_version = schema_version
        self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "subject": {
                "high": self.subject.high,
                "high_mid": self.subject.high_mid,
                "low_mid": self.subject.low_mid,
                "low": self.subject.low,
            },
            "predicate": {
                "high": self.predicate.high,
                "high_mid": self.predicate.high_mid,
                "low_mid": self.predicate.low_mid,
                "low": self.predicate.low,
            },
            "object": {
                "high": self.object.high,
                "high_mid": self.object.high_mid,
                "low_mid": self.object.low_mid,
                "low": self.object.low,
            },
            "provenance": self.provenance,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TripleRecord:
        """Create from dictionary format."""
        subj = data["subject"]
        pred = data["predicate"]
        objd = data["object"]

        subject = E((
            int(subj["high"]),
            int(subj.get("high_mid", 0)),
            int(subj.get("low_mid", 0)),
            int(subj["low"]),
        ))
        predicate = E((
            int(pred["high"]),
            int(pred.get("high_mid", 0)),
            int(pred.get("low_mid", 0)),
            int(pred["low"]),
        ))
        obj = E((
            int(objd["high"]),
            int(objd.get("high_mid", 0)),
            int(objd.get("low_mid", 0)),
            int(objd["low"]),
        ))

        record = cls(
            subject,
            predicate,
            obj,
            data.get("provenance"),
            data.get("schema_version", "v1"),
        )
        if "created_at" in data:
            record.created_at = data["created_at"]
        return record


def create_compound_key(subject: E, predicate: E) -> E:
    """Create compound key for subject+predicate -> object lookups."""
    # Combine each 64-bit lane with XOR to produce a deterministic 256-bit E
    a = subject.high ^ predicate.high
    b = subject.high_mid ^ predicate.high_mid
    c = subject.low_mid ^ predicate.low_mid
    d = subject.low ^ predicate.low
    return E((int(a), int(b), int(c), int(d)))


def create_reverse_key(predicate: E, obj: E) -> E:
    """Create reverse key for object+predicate -> subject lookups."""
    a = obj.high ^ predicate.high
    b = obj.high_mid ^ predicate.high_mid
    c = obj.low_mid ^ predicate.low_mid
    d = obj.low ^ predicate.low
    return E((int(a), int(b), int(c), int(d)))


class CidstoreClient:
    """
    Client wrapper for cidstore operations with error recovery and batching.

    Provides a standardized interface for:
    - Single and batch insertions
    - Compound key queries
    - Performance optimization
    - Retry logic with exponential backoff
    """

    def __init__(self, cidstore_impl):
        """Initialize with a cidstore implementation (real or mock)."""
        self.cidstore = cidstore_impl
        self.batch_size = 128  # Adaptive batch size, starts at 128
        self.max_batch_size = 1024
        self.min_batch_size = 32

    def insert_triple(self, triple: TripleRecord) -> bool:
        """Insert a single triple with compound keys for fast queries."""
        try:
            # Primary: subject+predicate -> object
            compound_key = create_compound_key(triple.subject, triple.predicate)
            self.cidstore.insert(compound_key, triple.object)

            # Secondary indices for reverse lookups
            self.cidstore.insert(
                triple.subject, triple.predicate
            )  # subject -> predicates
            self.cidstore.insert(
                triple.predicate, triple.object
            )  # predicate -> objects

            # Reverse lookup: object+predicate -> subject
            reverse_key = create_reverse_key(triple.predicate, triple.object)
            self.cidstore.insert(reverse_key, triple.subject)

            return True
        except Exception as e:
            print(f"Failed to insert triple: {e}")
            return False

    def batch_insert_triples(self, triples: List[TripleRecord]) -> Dict[str, Any]:
        """
        Insert multiple triples with optimized batching.

        Returns status dict with success count and any failures.
        """
        if not triples:
            return {"success_count": 0, "failures": []}

        # Prepare batch items for cidstore.batch_insert
        batch_items = []

        for triple in triples:
            # Primary compound key insertion
            compound_key = create_compound_key(triple.subject, triple.predicate)
            batch_items.append({
                "key": {
                    "high": compound_key.high,
                    "high_mid": compound_key.high_mid,
                    "low_mid": compound_key.low_mid,
                    "low": compound_key.low,
                },
                "value": {
                    "high": triple.object.high,
                    "high_mid": triple.object.high_mid,
                    "low_mid": triple.object.low_mid,
                    "low": triple.object.low,
                },
            })

            # Secondary indices
            batch_items.extend([
                {
                    "key": {
                        "high": triple.subject.high,
                        "high_mid": triple.subject.high_mid,
                        "low_mid": triple.subject.low_mid,
                        "low": triple.subject.low,
                    },
                    "value": {
                        "high": triple.predicate.high,
                        "high_mid": triple.predicate.high_mid,
                        "low_mid": triple.predicate.low_mid,
                        "low": triple.predicate.low,
                    },
                },
                {
                    "key": {
                        "high": triple.predicate.high,
                        "high_mid": triple.predicate.high_mid,
                        "low_mid": triple.predicate.low_mid,
                        "low": triple.predicate.low,
                    },
                    "value": {
                        "high": triple.object.high,
                        "high_mid": triple.object.high_mid,
                        "low_mid": triple.object.low_mid,
                        "low": triple.object.low,
                    },
                },
            ])

            # Reverse lookup key
            reverse_key = create_reverse_key(triple.predicate, triple.object)
            batch_items.append({
                "key": {
                    "high": reverse_key.high,
                    "high_mid": reverse_key.high_mid,
                    "low_mid": reverse_key.low_mid,
                    "low": reverse_key.low,
                },
                "value": {
                    "high": triple.subject.high,
                    "high_mid": triple.subject.high_mid,
                    "low_mid": triple.subject.low_mid,
                    "low": triple.subject.low,
                },
            })

        # Execute batch insertion with adaptive batch sizing
        success_count = 0
        failures = []

        for i in range(0, len(batch_items), self.batch_size):
            batch = batch_items[i : i + self.batch_size]
            try:
                self.cidstore.batch_insert(batch)
                # Calculate how many triples this batch represents
                # Each triple generates 4 batch items
                triples_in_batch = len(batch) // 4
                success_count += triples_in_batch
            except Exception as e:
                failures.append({"batch_start": i, "error": str(e)})

        return {"success_count": success_count, "failures": failures}

    def query_by_subject_predicate(self, subject: E, predicate: E) -> List[E]:
        """Find objects for a given subject+predicate."""
        compound_key = create_compound_key(subject, predicate)
        try:
            results = self.cidstore.lookup(compound_key)
            # Convert results back to E entities
            entities = []
            for r in results:
                if isinstance(r, tuple) and len(r) == 4:
                    entities.append(E(r))
                elif isinstance(r, E):
                    entities.append(r)
                else:
                    # Try to convert other formats
                    try:
                        entities.append(E(r))
                    except Exception:
                        pass
            return entities
        except Exception:
            return []

    def query_predicates_for_subject(self, subject: E) -> List[E]:
        """Find all predicates for a given subject."""
        try:
            results = self.cidstore.lookup(subject)
            entities = []
            for r in results:
                if isinstance(r, tuple) and len(r) == 4:
                    entities.append(E(r))
                elif isinstance(r, E):
                    entities.append(r)
                else:
                    # Try to convert other formats
                    try:
                        entities.append(E(r))
                    except Exception:
                        pass
            return entities
        except Exception:
            return []

    def query_subjects_by_object_predicate(self, obj: E, predicate: E) -> List[E]:
        """Find subjects for a given object+predicate (reverse lookup)."""
        reverse_key = create_reverse_key(predicate, obj)
        try:
            results = self.cidstore.lookup(reverse_key)
            entities = []
            for r in results:
                if isinstance(r, tuple) and len(r) == 4:
                    entities.append(E(r))
                elif isinstance(r, E):
                    entities.append(r)
                else:
                    # Try to convert other formats
                    try:
                        entities.append(E(r))
                    except Exception:
                        pass
            return entities
        except Exception:
            return []


def extract_context_to_triples(
    factoid_text: str, factoid_id: str, predicate_candidates: List[Dict[str, Any]]
) -> List[TripleRecord]:
    """
    Convert a factoid with predicate candidates into TripleRecord objects.

    This is a simplified implementation that demonstrates the conversion process.
    In a full implementation, this would use the SPO extraction and normalization pipeline.
    """
    triples = []

    # Generate subject and object entities from the factoid text
    # This is simplified - real implementation would use proper NLP extraction
    subject = E.from_str(f"subject_{factoid_id}")

    for candidate in predicate_candidates:
        predicate_cid = candidate.get("predicate_cid", "")
        if isinstance(predicate_cid, str) and predicate_cid:
            try:
                # Try to parse as JSON (entity dict) or create from string
                if predicate_cid.startswith("{"):
                    entity_data = json.loads(predicate_cid)
                    # Expect full 4-field entity dict in the greenfield design
                    predicate = E((
                        int(entity_data["high"]),
                        int(entity_data["high_mid"]),
                        int(entity_data["low_mid"]),
                        int(entity_data["low"]),
                    ))
                else:
                    predicate = E.from_str(predicate_cid)
            except (json.JSONDecodeError, KeyError):
                predicate = E.from_str(predicate_cid)

            # Generate object entity
            obj = E.from_str(f"object_{factoid_id}_{candidate.get('label', 'unknown')}")

            # Create provenance
            provenance = {
                "factoid_id": factoid_id,
                "factoid_text": factoid_text,
                "predicate_score": candidate.get("score", 1.0),
                "predicate_label": candidate.get("label", ""),
            }

            triple = TripleRecord(subject, predicate, obj, provenance)
            # compute triple hash and attach to provenance for metadata-triples
            try:
                hexdig, ehash = get_triple_hash(triple)
                triple.provenance["triple_hash"] = hexdig
                triple.provenance["triple_hash_e"] = ehash
            except Exception:
                # hashing should not break triple generation
                pass
            triples.append(triple)

    return triples


class PerformanceConfig:
    """Configuration for cidstore performance optimization."""

    def __init__(
        self,
        target_throughput_ops_per_sec: int = 1_000_000,
        target_latency_p99_microsec: int = 100,
        adaptive_batch_size: bool = True,
        retry_max_attempts: int = 3,
        retry_backoff_factor: float = 2.0,
    ):
        self.target_throughput_ops_per_sec = target_throughput_ops_per_sec
        self.target_latency_p99_microsec = target_latency_p99_microsec
        self.adaptive_batch_size = adaptive_batch_size
        self.retry_max_attempts = retry_max_attempts
        self.retry_backoff_factor = retry_backoff_factor


def robust_batch_insert_with_retry(
    cidstore_client: CidstoreClient,
    triples: List[TripleRecord],
    config: Optional[PerformanceConfig] = None,
) -> Dict[str, Any]:
    """
    Insert triples with retry logic and performance optimization.

    Implements the error recovery patterns described in the cidstore specs.
    """
    if config is None:
        config = PerformanceConfig()

    attempt = 0
    last_error = None

    while attempt < config.retry_max_attempts:
        try:
            result = cidstore_client.batch_insert_triples(triples)

            if not result["failures"]:
                return result

            # If there were partial failures, retry only the failed items
            # This is a simplified implementation - real version would extract
            # failed triples from the batch_items mapping
            if attempt < config.retry_max_attempts - 1:
                time.sleep(config.retry_backoff_factor**attempt)
                attempt += 1
                continue
            else:
                return result

        except Exception as e:
            last_error = e
            if attempt < config.retry_max_attempts - 1:
                time.sleep(config.retry_backoff_factor**attempt)
                attempt += 1
            else:
                break

    # All retries failed
    return {
        "success_count": 0,
        "failures": [{"error": f"All retries failed: {last_error}"}],
    }
