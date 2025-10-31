# Triple Storage and Query Patterns for cidstore Integration

## Overview

This document details how cidsem triples are stored in cidstore and the supported query patterns based on the cidstore key-value model.

## Storage Strategy

### Primary Pattern: Compound Keys
Each triple `(subject: E, predicate: E, object: E)` is stored using compound keys optimized for the most common query pattern:

```python
# Most common query: "Given subject and predicate, get all objects"
compound_key = create_compound_key(subject, predicate)
# Send via ZMQ msgpack to cidstore
zmq_insert(compound_key, object)

# Compound key creation (deterministic, 256-bit E entities)
def create_compound_key(subject: E, predicate: E) -> E:
    # Combine 4×64-bit parts to create deterministic compound key
    combined_high = subject.high ^ predicate.high
    combined_high_mid = subject.high_mid ^ predicate.high_mid
    combined_low_mid = subject.low_mid ^ predicate.low_mid
    combined_low = subject.low ^ predicate.low
    return E(high=combined_high, high_mid=combined_high_mid,
             low_mid=combined_low_mid, low=combined_low)
```

### Secondary Indices (Optional)
For less common query patterns, additional indices may be maintained:

```python
# Reverse lookup: "Given predicate and object, find all subjects"
reverse_compound_key = create_compound_key(predicate, object)
zmq_insert(reverse_compound_key, subject)

# Predicate index: "Get all predicates for a subject"
zmq_insert(subject, predicate)

# Object index: "Get all objects with a specific predicate"
zmq_insert(predicate, object)
```

Note: All inserts use ZMQ/msgpack for performance (see spec11-cidstore-integration.md)

## Query Patterns

### 1. Forward Triple Lookup (Primary)
**Query**: "What objects are related to subject X via predicate Y?"
```python
def query_objects(subject: E, predicate: E) -> List[E]:
    compound_key = create_compound_key(subject, predicate)
    # Use ZMQ query command
    return zmq_query(compound_key)

# Example: Get all locations where Alice lives
alice = E.from_content("alice")  # 256-bit SHA-256
lives_in = E.from_content("livesIn")
locations = query_objects(alice, lives_in)
```

### 2. Reverse Triple Lookup (Secondary)
**Query**: "What subjects are related to object Z via predicate Y?"
```python
def query_subjects(predicate: E, object: E) -> List[E]:
    reverse_key = create_compound_key(predicate, object)
    return cidstore.lookup(reverse_key)

# Example: Who lives in Berlin?
berlin = E.from_str("Berlin")
lives_in = E.from_str("livesIn")
residents = query_subjects(lives_in, berlin)
```

### 3. Predicate Discovery
**Query**: "What predicates apply to subject X?"
```python
def query_predicates(subject: E) -> List[E]:
    return cidstore.lookup(subject)

# Example: What relationships does Alice have?
alice = E.from_str("alice")
predicates = query_predicates(alice)
```

### 4. Full Triple Enumeration
**Query**: "Get all triples with predicate Y"
```python
def query_all_triples_with_predicate(predicate: E) -> List[Tuple[E, E, E]]:
    objects = cidstore.lookup(predicate)
    triples = []

    for obj in objects:
        # Find all subjects that have this predicate->object relationship
        reverse_key = create_compound_key(predicate, obj)
        subjects = cidstore.lookup(reverse_key)

        for subject in subjects:
            triples.append((subject, predicate, obj))

    return triples
```

## Performance Characteristics

### Query Performance by Pattern
| Query Pattern | Storage Overhead | Lookup Performance | Use Case Frequency |
|---------------|------------------|-------------------|-------------------|
| Subject+Predicate→Objects | 1x | O(1) avg, O(k) worst | 80% (primary) |
| Predicate+Object→Subjects | 2x | O(1) avg, O(k) worst | 15% (secondary) |
| Subject→Predicates | 2x | O(1) avg, O(p) worst | 4% (discovery) |
| Full predicate enumeration | 2x | O(n) linear scan | 1% (analytics) |

Where:
- k = number of objects for subject+predicate
- p = number of predicates for subject
- n = total number of triples

### Batch Insertion Optimization
```python
import zmq
import msgpack

def insert_triples_optimized(triples: List[Tuple[E, E, E]]):
    """Insert triples with optimized batching via ZMQ/msgpack."""

    # Connect to CIDStore
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.connect('tcp://cidstore:5555')

    # Group by index type for batch efficiency
    primary_batch = []      # compound_key -> object
    reverse_batch = []      # reverse_key -> subject

    for subject, predicate, obj in triples:
        # Primary index (most important)
        primary_key = create_compound_key(subject, predicate)
        primary_batch.append({
            's': f"E({primary_key.high},{primary_key.high_mid},{primary_key.low_mid},{primary_key.low})",
            'p': f"E({obj.high},{obj.high_mid},{obj.low_mid},{obj.low})",
            'o': f"E(0,0,0,0)"  # Placeholder for triple storage
        })

        # Secondary indices (optional based on query requirements)
        if ENABLE_REVERSE_LOOKUP:
            reverse_key = create_compound_key(predicate, obj)
            reverse_batch.append({
                's': f"E({reverse_key.high},{reverse_key.high_mid},{reverse_key.low_mid},{reverse_key.low})",
                'p': f"E({subject.high},{subject.high_mid},{subject.low_mid},{subject.low})",
                'o': f"E(0,0,0,0)"
            })

    # Batch insert via ZMQ
    msg = {'command': 'batch_insert', 'triples': primary_batch}
    sock.send(msgpack.packb(msg, use_bin_type=True))
    resp = msgpack.unpackb(sock.recv(), raw=False)

    if reverse_batch and ENABLE_REVERSE_LOOKUP:
        msg = {'command': 'batch_insert', 'triples': reverse_batch}
        sock.send(msgpack.packb(msg, use_bin_type=True))
        resp = msgpack.unpackb(sock.recv(), raw=False)

    return resp
```

## Index Configuration

### Configuration Options
```python
class TripleStorageConfig:
    def __init__(self):
        # Primary index (always enabled)
        self.enable_primary_index = True

        # Secondary indices (configurable based on query requirements)
        self.enable_reverse_lookup = True    # +100% storage, enables predicate+object->subjects
        self.enable_predicate_index = False  # +50% storage, enables subject->predicates
        self.enable_object_index = False     # +50% storage, enables predicate->objects

        # Performance tuning
        self.batch_size = 512
        self.auto_tune_batch_size = True
        self.target_latency_us = 50
        self.max_storage_overhead = 2.0  # 2x storage max
```

### Recommended Configurations

#### High-Performance Read (Default)
```python
config = TripleStorageConfig()
config.enable_reverse_lookup = True   # Support both forward and reverse queries
config.enable_predicate_index = False # Skip to minimize storage overhead
config.enable_object_index = False    # Skip to minimize storage overhead
# Result: 2x storage overhead, supports 95% of query patterns efficiently
```

#### Analytics/Discovery Workload
```python
config = TripleStorageConfig()
config.enable_reverse_lookup = True
config.enable_predicate_index = True  # Enable for subject->predicates discovery
config.enable_object_index = True     # Enable for predicate->objects enumeration
# Result: 3x storage overhead, supports all query patterns efficiently
```

#### Minimal Storage
```python
config = TripleStorageConfig()
config.enable_reverse_lookup = False  # Primary index only
config.enable_predicate_index = False
config.enable_object_index = False
# Result: 1x storage overhead, forward queries only, reverse queries require full scan
```

This storage strategy balances query performance with storage efficiency, providing sub-microsecond lookups for the most common triple query patterns while maintaining compatibility with cidstore's key-value model and performance characteristics.