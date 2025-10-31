# CIDStore Integration Specification

## Overview

This document specifies how CIDSEM integrates with CIDStore for persistent triple storage. CIDStore provides both a REST control/monitoring API and a high-performance ZMQ/msgpack data plane for bulk operations.

## Architecture

### CIDStore Services

CIDStore exposes two distinct planes:

1. **Control Plane (REST API)**: Health checks, metrics, runtime configuration
   - Default port: 8000
   - Protocol: HTTP/JSON (FastAPI)
   - Use case: Monitoring, configuration, debugging

2. **Data Plane (ZMQ/msgpack)**: High-throughput data operations
   - Default ports: 5555 (REQ/REP), 5557 (PUSH/PULL), 5558 (ROUTER/DEALER), 5559 (PUB/SUB)
   - Protocol: ZeroMQ with MessagePack encoding
   - Use case: Triple insertion, queries, bulk operations

### Integration Principle

**IMPORTANT**: CIDSEM must NOT use REST for bulk data operations. All triple insertions, queries, and bulk operations must use ZMQ with msgpack encoding for performance (target >1M ops/sec).

## Content Identifier Format (256-bit CIDs)

### E Entity Structure

CIDStore uses full SHA-256 (256 bits) for content identifiers, represented as four 64-bit unsigned integers:

```python
class E:
    high: uint64       # bits 255-192
    high_mid: uint64   # bits 191-128
    low_mid: uint64    # bits 127-64
    low: uint64        # bits 63-0
```

### CID Representations

CIDs can be expressed in multiple formats:

1. **String format** (canonical): `"E(h,hm,lm,l)"`
   - Example: `"E(12345,67890,11121,31415)"`
   - Where h, hm, lm, l are the four 64-bit unsigned integer components

2. **List/Tuple**: `[high, high_mid, low_mid, low]`
   - Example: `[12345, 67890, 11121, 31415]`

3. **Struct format** (msgpack/JSON):
   ```json
   {
     "high": 12345,
     "high_mid": 67890,
     "low_mid": 11121,
     "low": 31415
   }
   ```

4. **JACK hexdigest**: `"j:abcd..."`
   - Server converts to E numeric form automatically

### Legacy Note

CIDStore retains compatibility with 128-bit (2-part) CIDs in some places, but CIDSEM should always use the full 4-part format for unambiguous behavior.

## REST Control API

Base URL: `http://<cidstore-host>:8000`

### Health & Readiness

- **GET /health**
  - Returns: `200 OK` with plain text `"ok"` when control plane is running
  - Use: Deployment health checks

- **GET /ready**
  - Returns: `200 OK` with plain text `"ready"` when service is ready
  - Use: Kubernetes readiness probes

### Metrics

- **GET /metrics/prometheus**
  - Returns: Prometheus text exposition format (if `prometheus_client` installed)
  - Returns: `501` if not available
  - Use: Prometheus scraping

- **GET /metrics**
  - Returns: Simple text metrics listing
  - Use: Quick metrics overview

### Runtime Configuration

- **GET /config/promotion_threshold**
  - Returns: `{"promotion_threshold": <int>, "version": "1.0"}`
  - Use: Check current promotion threshold

- **PUT /config/promotion_threshold**
  - Body: `{"promotion_threshold": <int>}`
  - Headers: `Authorization: Bearer <jwt_token>`
  - Returns: `{"promotion_threshold": <int>, "version": "1.0"}`
  - Use: Update promotion threshold at runtime

- **GET /config/batch_size**
  - Returns: `{"batch_size": <int>, "version": "1.0"}`

- **PUT /config/batch_size**
  - Body: `{"batch_size": <int>}`
  - Headers: `Authorization: Bearer <jwt_token>`
  - Returns: `{"batch_size": <int>, "version": "1.0"}`
  - Use: Tune batch size for performance

### Debug Endpoints (Internal-Only)

- **GET /debug/bucket/{bucket_id}**
  - Internal-only: checks caller IP or `X-Internal-Test` header
  - Returns: Bucket metadata for diagnostics

- **GET /debug/get?high=<>&high_mid=<>&low_mid=<>&low=<>**
  - Query by four 64-bit components
  - Returns: Serialized results from store for the composed key

- **POST /debug/delete**
  - Body (4-part form):
    ```json
    {
      "high": <int>,
      "high_mid": <int>,
      "low_mid": <int>,
      "low": <int>
    }
    ```
  - Internal-only or auth protected in production

## ZMQ Data Plane

### MessagePack Conventions

All messages use MessagePack encoding:
- **Pack**: `msgpack.packb(obj, use_bin_type=True)`
- **Unpack**: `msgpack.unpackb(buf, raw=False)`
- All responses include a `version` field: `"1.0"`
- Error responses: `{"error_code": int, "error_msg": str, "version": "1.0"}`

### Socket Endpoints

Default addresses (configurable via environment variables):

- **REQ/REP (compat)**: `tcp://<host>:5555`
  - Environment: `CIDSTORE_ZMQ_ENDPOINT`
  - Use: Simple request/response pattern for tests and simple clients

- **PUSH/PULL (mutations)**: `tcp://<host>:5557`
  - Environment: `CIDSTORE_PUSH_PULL_ADDR`
  - Use: High-throughput mutation queue (single-writer pattern)

- **ROUTER/DEALER (reads)**: `tcp://<host>:5558`
  - Environment: `CIDSTORE_ROUTER_DEALER_ADDR`
  - Use: Concurrent reads with identity frames

- **PUB/SUB (notifications)**: `tcp://<host>:5559`
  - Environment: `CIDSTORE_PUB_SUB_ADDR`
  - Use: Event/heartbeat notifications

### Binding and Networking

**CRITICAL**: By default, PUSH/ROUTER/PUB addresses bind to `127.0.0.1` (loopback only). For cross-container communication, configure them to bind to `0.0.0.0`:

```yaml
environment:
  - CIDSTORE_ZMQ_ENDPOINT=tcp://0.0.0.0:5555
  - CIDSTORE_PUSH_PULL_ADDR=tcp://0.0.0.0:5557
  - CIDSTORE_ROUTER_DEALER_ADDR=tcp://0.0.0.0:5558
  - CIDSTORE_PUB_SUB_ADDR=tcp://0.0.0.0:5559
```

## REQ/REP Pattern (Recommended for CIDSEM)

The REQ/REP compat endpoint is the recommended integration path for CIDSEM test harnesses and simple agents.

### Batch Insert

**Request**:
```python
{
  "command": "batch_insert",
  "triples": [
    {
      "s": "E(1,2,3,4)",
      "p": "E(5,6,7,8)",
      "o": "E(9,10,11,12)"
    },
    # ... more triples
  ]
}
```

**Response (success)**:
```python
{
  "status": "ok",
  "inserted": 123,
  "version": "1.0"
}
```

### Single Insert

**Request**:
```python
{
  "command": "insert",
  "s": "E(1,2,3,4)",
  "p": "E(5,6,7,8)",
  "o": "E(9,10,11,12)"
}
```

**Response**:
```python
{
  "status": "ok",
  "version": "1.0"
}
```

### Query

**Request**:
```python
{
  "command": "query",
  "s": "E(1,2,3,4)",
  "p": "E(5,6,7,8)",
  "o": "E(9,10,11,12)"  # optional
}
```

**Response (success)**:
```python
{
  "results": [
    # ... matching triples
  ],
  "version": "1.0"
}
```

### Python Client Example

```python
import zmq
import msgpack

# Connect to CIDStore
ctx = zmq.Context()
sock = ctx.socket(zmq.REQ)
sock.connect('tcp://cidstore:5555')

# Prepare batch insert message
msg = {
    'command': 'batch_insert',
    'triples': [
        {
            's': 'E(12345,67890,11121,31415)',
            'p': 'E(23456,78901,21222,41516)',
            'o': 'E(34567,89012,31323,51617)'
        }
    ]
}

# Send request
sock.send(msgpack.packb(msg, use_bin_type=True))

# Receive response
resp = msgpack.unpackb(sock.recv(), raw=False)
print(resp)  # {"status": "ok", "inserted": 1, "version": "1.0"}
```

## PUSH/PULL Pattern (Production)

For maximum throughput in production, use the PUSH/PULL mutation queue.

### Mutation Message Format

**Single Insert**:
```python
{
  "op_code": "INSERT",
  "key": "E(1,2,3,4)",
  "value": "E(5,6,7,8)"
}
```

**Batch Insert**:
```python
{
  "op_code": "BATCH_INSERT",
  "entries": [
    {
      "key": "E(1,2,3,4)",
      "value": "E(5,6,7,8)"
    },
    # ... more entries
  ]
}
```

**Python Producer Example**:
```python
import zmq
import msgpack

ctx = zmq.Context()
sock = ctx.socket(zmq.PUSH)
sock.connect('tcp://cidstore:5557')

# Send mutation (fire-and-forget)
mutation = {
    'op_code': 'BATCH_INSERT',
    'entries': [
        {'key': 'E(1,2,3,4)', 'value': 'E(5,6,7,8)'}
    ]
}
sock.send(msgpack.packb(mutation, use_bin_type=True))
```

## ROUTER/DEALER Pattern (Concurrent Reads)

For concurrent read queries from multiple clients.

### Message Format

Client sends multipart frames:
1. Identity frame (managed by ROUTER/DEALER)
2. Empty delimiter
3. Msgpack payload

Supported op_codes: `LOOKUP`, `METRICS`

## PUB/SUB Pattern (Notifications)

Subscribe to store events and heartbeats.

### Notification Format

```python
{
  "type": "heartbeat",  # or other event types
  "args": [...]
}
```

Heartbeat: Published every second while server is running.

**Python Subscriber Example**:
```python
import zmq
import msgpack

ctx = zmq.Context()
sock = ctx.socket(zmq.SUB)
sock.connect('tcp://cidstore:5559')
sock.setsockopt(zmq.SUBSCRIBE, b'')  # Subscribe to all

while True:
    msg = msgpack.unpackb(sock.recv(), raw=False)
    if msg['type'] == 'heartbeat':
        print("CIDStore is alive")
```

## Performance Targets

### Throughput
- **Batched operations**: >1M ops/sec
- **Batch size**: 32-1024 items (adaptive)

### Latency
- **Average**: <50μs
- **P99**: <100μs

### Optimization Guidelines

1. **Use batching**: Group triples into batches of 32-1024 items
2. **Auto-tune batch size**: Monitor latency and adjust batch size dynamically
3. **Use PUSH/PULL for production**: REQ/REP for testing only
4. **Pre-pack messages**: Serialize msgpack once per batch
5. **Connection pooling**: Reuse ZMQ contexts and sockets

## Docker Compose Configuration

```yaml
services:
  cidstore:
    image: cidstore:latest
    ports:
      - "8000:8000"    # REST API
      - "5555:5555"    # REQ/REP compat
      - "5557:5557"    # PUSH/PULL mutations
      - "5558:5558"    # ROUTER/DEALER reads
      - "5559:5559"    # PUB/SUB notifications
    environment:
      - CIDSTORE_HDF5_PATH=/data/cidstore.h5
      - CIDSTORE_ZMQ_ENDPOINT=tcp://0.0.0.0:5555
      - CIDSTORE_PUSH_PULL_ADDR=tcp://0.0.0.0:5557
      - CIDSTORE_ROUTER_DEALER_ADDR=tcp://0.0.0.0:5558
      - CIDSTORE_PUB_SUB_ADDR=tcp://0.0.0.0:5559
    volumes:
      - cidstore-data:/data

  cidsem:
    build: .
    depends_on:
      - cidstore
    environment:
      - CIDSTORE_HOST=cidstore
      - CIDSTORE_REST_PORT=8000
      - CIDSTORE_ZMQ_PORT=5555

volumes:
  cidstore-data:
```

## CIDSEM Integration Checklist

### 1. Health & Readiness
- Poll `http://cidstore:8000/health` until it returns `ok` before starting operations
- Use `/ready` for Kubernetes readiness probes

### 2. Batch Insert (Test/Development)
- Use REQ/REP to `tcp://cidstore:5555`
- Send `batch_insert` msgpack messages
- Wait for `{"status": "ok"}` responses

### 3. Batch Insert (Production)
- Use PUSH to `tcp://cidstore:5557`
- Send `op_code: "BATCH_INSERT"` messages
- No response expected (fire-and-forget for throughput)

### 4. Queries
- Use REQ/REP `query` command
- Or ROUTER/DEALER for concurrent queries

### 5. Monitoring
- Subscribe to PUB socket for heartbeat and event notifications
- Use REST `/metrics` endpoint for operational metrics
- Use REST `/metrics/prometheus` for Prometheus scraping

### 6. Configuration
- Use REST `/config/*` endpoints to tune parameters at runtime
- Requires JWT authentication (Bearer token)

## Error Handling

### Error Response Format

```python
{
  "error_code": 500,
  "error_msg": "Internal error description",
  "version": "1.0"
}
```

### Retry Strategy

1. **Network errors**: Exponential backoff (100ms, 200ms, 400ms, ...)
2. **Partial failures**: Re-send only failed items
3. **Idempotency**: Safe to retry batch_insert with same data
4. **WAL-backed**: CIDStore ensures consistency on retry

## Security Notes

### Authentication
- JWT helper in `src/cidstore/auth.py` is a demo stub
- Replace with proper JWT verification (PyJWT) in production
- Secure secrets via environment variables

### Network Isolation
- Use network-level controls for ZMQ endpoints
- Consider mTLS for secure communication
- Use separate internal networks in production

### Internal-Only Endpoints
- Debug endpoints check caller IP
- Use `X-Internal-Test: 1` header for testing
- Disable or restrict in production

## References

- CIDStore Interface Document: `docs/cidstore interface.md`
- Test Implementation: `tests/cidsem_mockup/cidsem_test.py`
- ZeroMQ Documentation: https://zeromq.org/
- MessagePack Documentation: https://msgpack.org/
