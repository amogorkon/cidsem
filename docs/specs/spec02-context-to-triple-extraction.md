# 2. Context-to-Triple Extraction for cidstore

## 2.1 Core Purpose

cidsem transforms arbitrary input contexts into (subject: E, predicate: E, object: E) triples suitable for direct storage in cidstore. All triple elements are 128-bit entity identifiers compatible with the cidstore.E class.

## 2.2 Input Contexts

cidsem accepts arbitrary structured or semi-structured data:

### Supported Context Types
- **JSON objects**: `{"user": "alice", "action": "login", "timestamp": "2024-06-01T12:00:00Z"}`
- **Python dictionaries**: Key-value pairs with nested structures
- **Event records**: Log entries, audit trails, system events
- **Document metadata**: Structured document properties and relationships
- **Nested structures**: Lists, arrays, complex hierarchical data

### Context Requirements
- Must be deterministically serializable (consistent key ordering)
- Should contain meaningful entities and relationships
- May include temporal, spatial, or categorical metadata

## 2.3 E Entity Generation

All entities (subjects, predicates, objects) are generated as 128-bit E entities compatible with cidstore.

### E Creation Methods
```python
from cidstore.keys import E

# From string content (uses UUID5 internally)
entity = E.from_str("alice")
entity = E.from_str("login_action_2024-06-01")
entity = E.from_str("https://example.com/doc123")

# Direct access to high/low components
print(f"High: {entity.high}, Low: {entity.low}")

# Serialization for JSON/msgpack
serialized = {"high": entity.high, "low": entity.low}
```

### Deterministic Entity Rules
- **Same string content** → **Same E entity** (idempotent)
- **Canonicalization**: Normalize strings before E.from_str() (lowercase, trim, etc.)
- **Composite entities**: For complex objects, create deterministic string representations

## 2.4 Triple Extraction Patterns

### Basic Property Extraction
```python
# Input context
context = {"user": "alice", "role": "admin", "active": True}

# Output triples
triples = [
    (E.from_str("alice"), E.from_str("hasRole"), E.from_str("admin")),
    (E.from_str("alice"), E.from_str("isActive"), E.from_str("true"))
]
```

### Relationship Extraction
```python
# Input context
context = {"user": "alice", "follows": ["bob", "charlie"], "timestamp": "2024-06-01"}

# Output triples
triples = [
    (E.from_str("alice"), E.from_str("follows"), E.from_str("bob")),
    (E.from_str("alice"), E.from_str("follows"), E.from_str("charlie")),
    (E.from_str("alice"), E.from_str("timestamp"), E.from_str("2024-06-01"))
]
```

### Event Extraction
```python
# Input context
context = {
    "event_type": "user_login",
    "user": "alice",
    "ip_address": "192.168.1.1",
    "timestamp": "2024-06-01T12:00:00Z",
    "success": True
}

# Output triples
triples = [
    (E.from_str("user_login_2024-06-01T12:00:00Z"), E.from_str("eventType"), E.from_str("user_login")),
    (E.from_str("user_login_2024-06-01T12:00:00Z"), E.from_str("actor"), E.from_str("alice")),
    (E.from_str("user_login_2024-06-01T12:00:00Z"), E.from_str("sourceIP"), E.from_str("192.168.1.1")),
    (E.from_str("user_login_2024-06-01T12:00:00Z"), E.from_str("timestamp"), E.from_str("2024-06-01T12:00:00Z")),
    (E.from_str("user_login_2024-06-01T12:00:00Z"), E.from_str("outcome"), E.from_str("success"))
]
```

## 2.5 cidstore Integration

### Network Protocol (msgpack serialization)
All network communication with cidstore uses msgpack serialization over ZMQ. E entities are serialized as maps with high/low fields:

```python
# E entity serialization format
entity_msgpack = {
    "high": 12345678901234567890,  # uint64 high bits
    "low": 9876543210987654321    # uint64 low bits
}

# Batch operations use arrays of these objects
batch_insert = [
    {"key": {"high": ..., "low": ...}, "value": {"high": ..., "low": ...}},
    {"key": {"high": ..., "low": ...}, "value": {"high": ..., "low": ...}}
]
```

### Triple Storage Model
cidsem outputs triples as (subject: E, predicate: E, object: E). Each triple is stored as a key-value pair optimized for subject-predicate-object lookups:

```python
# Primary storage pattern: subject-predicate as compound key, object as value
# Most common query: "Given subject and predicate, get all objects"
for subject, predicate, obj in triples:
    compound_key = create_compound_key(subject, predicate)
    cidstore.insert(compound_key, obj)

# Alternative: separate indices for different query patterns
# Forward index: subject -> {predicate: [objects]}
cidstore.insert(subject, predicate)  # subject has predicate
cidstore.insert(predicate, obj)      # predicate points to object

# Reverse index (if needed): object -> {predicate: [subjects]}
cidstore.insert(obj, predicate)      # object referenced by predicate
cidstore.insert(predicate, subject)  # predicate originates from subject
```

### Performance Requirements
```python
# Target performance metrics
TARGET_THROUGHPUT = 1_000_000  # ops/sec (batched)
BATCH_SIZE_RANGE = (32, 1024)  # adaptive batch sizing
TARGET_LATENCY_AVG = 50e-6     # 50μs average
TARGET_LATENCY_P99 = 100e-6    # 100μs P99

class PerformanceConfig:
    def __init__(self):
        self.batch_size = 256  # start with middle value
        self.flush_interval = 0.001  # 1ms
        self.auto_tune = True

    def adjust_batch_size(self, observed_latency, throughput):
        """Auto-tune batch size based on performance metrics."""
        if observed_latency > TARGET_LATENCY_P99:
            self.batch_size = max(32, self.batch_size // 2)
        elif throughput < TARGET_THROUGHPUT * 0.8:
            self.batch_size = min(1024, self.batch_size * 2)
```

### Batch Insertion with Performance Optimization
```python
def insert_triples_batch(cidstore, triples, config=PerformanceConfig()):
    """Insert triples in performance-optimized batches."""
    batch = []

    for subject, predicate, obj in triples:
        # Create compound key for primary storage pattern
        compound_key = create_compound_key(subject, predicate)
        batch.append({"key": compound_key.to_msgpack(), "value": obj.to_msgpack()})

        # Flush batch when size limit reached
        if len(batch) >= config.batch_size:
            cidstore.batch_insert(batch)
            batch = []

    # Flush remaining items
    if batch:
        cidstore.batch_insert(batch)
```

### Provenance Meta-Triples
Track extraction provenance using additional meta-triples:

```python
# Original context -> extraction metadata
context_id = E.from_str(f"context_{hash(json.dumps(context, sort_keys=True))}")
extractor_id = E.from_str("cidsem_v1.0")
timestamp_id = E.from_str(datetime.utcnow().isoformat())

# Meta-triples for provenance
meta_triples = [
    (context_id, E.from_str("extractedBy"), extractor_id),
    (context_id, E.from_str("extractedAt"), timestamp_id),
    (triple_id, E.from_str("derivedFrom"), context_id)  # for each generated triple
]
```

## 2.6 Extraction Rules Engine

### Rule-Based Extraction (Symbolic)
```python
class ExtractionRule:
    def matches(self, context: dict) -> bool:
        """Return True if this rule applies to the context."""
        pass

    def extract(self, context: dict) -> List[Tuple[E, E, E]]:
        """Extract triples from the context."""
        pass

# Example rule for user events
class UserEventRule(ExtractionRule):
    def matches(self, context):
        return "user" in context and "action" in context

    def extract(self, context):
        user_e = E.from_str(context["user"])
        action_e = E.from_str(context["action"])
        performed_e = E.from_str("performed")

        triples = [(user_e, performed_e, action_e)]

        if "timestamp" in context:
            timestamp_e = E.from_str(context["timestamp"])
            when_e = E.from_str("timestamp")
            triples.append((user_e, when_e, timestamp_e))

        return triples
```

### Confidence and Validation
```python
class ExtractionResult:
    def __init__(self, triples: List[Tuple[E, E, E]], confidence: float, rule_id: str):
        self.triples = triples
        self.confidence = confidence  # 0.0 - 1.0
        self.rule_id = rule_id

    def should_auto_insert(self) -> bool:
        """High-confidence extractions can be auto-inserted."""
        return self.confidence >= 0.9

    def needs_validation(self) -> bool:
        """Low-confidence extractions need human/bot validation."""
        return 0.3 <= self.confidence < 0.9
```

## 2.7 API Integration

### Core Extraction Interface
```python
class CidsemExtractor:
    def extract_triples(self, context: dict) -> ExtractionResult:
        """Extract triples from arbitrary context."""
        pass

    def insert_to_cidstore(self, cidstore, result: ExtractionResult):
        """Insert extraction result into cidstore."""
        if result.should_auto_insert():
            self._batch_insert(cidstore, result.triples)
        elif result.needs_validation():
            self._queue_for_validation(result)
        else:
            self._queue_for_dreaming(result)
```

### REST API Endpoints with Performance Optimization
```python
# POST /extract
# Body: {"context": {...}, "auto_insert": true/false, "batch_config": {...}}
# Response: {
#   "triples": [{"subject": {"high": ..., "low": ...}, "predicate": {...}, "object": {...}}],
#   "confidence": 0.95,
#   "inserted": true/false,
#   "performance": {"latency_ms": 0.05, "throughput_ops_sec": 1200000}
# }

# POST /batch_extract (high-performance endpoint)
# Body: {
#   "contexts": [{...}, {...}],
#   "batch_config": {"size": 512, "auto_tune": true},
#   "serialization": "msgpack"  # for maximum performance
# }
# Response: {
#   "results": [{"triples": [...], "confidence": 0.95, "inserted": true}],
#   "performance": {"total_latency_ms": 2.3, "avg_throughput_ops_sec": 980000},
#   "batch_stats": {"batch_size_used": 512, "auto_tuned": false}
# }

# POST /cidstore/batch_insert (direct cidstore integration)
# Body: msgpack-encoded array of {"key": {"high": ..., "low": ...}, "value": {"high": ..., "low": ...}}
# Response: {"results": [{"status": "ok"|"error", "message": ""}], "performance": {...}}
```

## 2.8 Error Recovery and Retry Strategies

### WAL-Based Crash Recovery
```python
class CidstoreClient:
    def __init__(self):
        self.wal_enabled = True  # All operations are WAL-logged
        self.retry_config = RetryConfig()

    def insert_with_recovery(self, key, value):
        """Insert with automatic retry and crash recovery."""
        try:
            # All inserts are idempotent and WAL-logged
            result = self.cidstore.insert(key, value)
            return result
        except NetworkError as e:
            # Exponential backoff retry
            return self.retry_with_backoff(self.cidstore.insert, key, value)
        except PartialFailureError as e:
            # Re-send failed subset only
            return self.retry_failed_subset(e.failed_items)

class RetryConfig:
    def __init__(self):
        self.max_retries = 5
        self.base_delay = 0.1  # 100ms
        self.backoff_factor = 2.0
        self.max_delay = 10.0  # 10 seconds
```

### Idempotency and Partial Failure Handling
```python
def robust_batch_insert(cidstore, triples):
    """Batch insert with comprehensive error handling."""
    batch = prepare_batch(triples)

    try:
        result = cidstore.batch_insert(batch)
        return result

    except PartialFailureError as e:
        # Some items failed - retry only the failed ones
        failed_items = e.get_failed_items()
        return retry_failed_items(cidstore, failed_items)

    except NetworkError as e:
        # Network failure - retry entire batch (idempotent)
        time.sleep(calculate_backoff_delay(attempt_count))
        return robust_batch_insert(cidstore, triples)

    except ValidationError as e:
        # Invalid data - log and skip
        logger.error(f"Invalid triple data: {e}")
        return {"status": "partial_success", "errors": e.details}
```

### Background GC and Deletion Handling
```python
# Deletions are logged separately and handled by background GC
# All deletion operations are idempotent and safe to repeat
def delete_triples(cidstore, triples_to_delete):
    """Delete triples with GC logging."""
    for subject, predicate, obj in triples_to_delete:
        # Deletion is logged to DeletionLog for background GC
        cidstore.delete(subject, predicate)  # Logged automatically
        cidstore.delete(predicate, obj)      # Background GC will clean up
```

## 2.9 Implementation Constraints

### Deterministic Requirements
- **Same context** → **Same triples** (idempotent)
- **Stateless extraction**: No dependency on previous contexts
- **Canonical ordering**: Consistent triple ordering for batch operations
- **msgpack serialization**: Consistent E entity serialization format

### Performance Requirements
- **Target throughput**: >1M ops/sec (batched)
- **Batch sizes**: 32-1024 triples, auto-tuned based on latency
- **Memory efficiency**: Stream processing without loading all contexts
- **Adaptive tuning**: Dynamic batch size and flush interval adjustment

### Error Handling
- **WAL recovery**: Automatic replay of incomplete operations after crash
- **Idempotent operations**: Safe to retry inserts/deletes on failure
- **Exponential backoff**: Network error retry with increasing delays
- **Partial failure recovery**: Re-send only failed items from batch operations

This specification provides the foundation for implementing cidsem as a deterministic, stateless context-to-triple extraction system fully compatible with cidstore's 128-bit E entity model and persistence layer.