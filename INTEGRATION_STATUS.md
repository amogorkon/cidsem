# CIDStore + Redis Integration Status

## Current Setup (November 2, 2025)

✅ **Docker Compose Stack Running**
- cidstore: `Up 2 minutes (healthy)`
- redis: `Up 2 minutes`

### Ports Exposed
| Port | Service | Protocol | Purpose |
|------|---------|----------|---------|
| 8000 | cidstore | REST/HTTP | Health checks, control API |
| 5555 | cidstore | ZMQ REQ/REP | Request-response pattern |
| 5556 | cidstore | ZMQ PUSH/PULL | Mutations and writes |
| 5557 | cidstore | ZMQ PUB/SUB | Notifications and broadcasts |
| 6379 | redis | Redis | Key-value store |

### Environment Variables (cidstore service)
```yaml
CIDSTORE_PORT=8000
CIDSTORE_ZMQ_REQREP_PORT=5555
CIDSTORE_ZMQ_PUSH_PORT=5556
CIDSTORE_ZMQ_PUB_PORT=5557
CIDSTORE_HDF5_PATH=/data/cidstore.h5
PYTHONUNBUFFERED=1
PYTHON_JIT=1
REDIS_HOST=redis
REDIS_PORT=6379
```

### Verified Working
- ✅ `curl http://localhost:8000/health` → `ok`
- ✅ `docker exec redis redis-cli ping` → `PONG`
- ✅ HDF5 storage initialized (`/data/cidstore.h5`)
- ✅ WAL (Write-Ahead Log) initialized and operational
- ✅ Network connectivity between services via `app-network`

## CIDSem Redis Integration

### Code Changes Made
1. **Added redis dependency** to `pyproject.toml`:
   ```toml
   redis = "^4.6.0"
   ```

2. **Modified `src/cidsem/cidstore.py`**:
   - Added optional Redis client initialization in `CidstoreClient.__init__`
   - Reads environment variables:
     - `CIDSEM_USE_REDIS` (default "1")
     - `REDIS_HOST` (default "redis")
     - `REDIS_PORT` (default "6379")
   - Graceful fallback if Redis unavailable
   - After inserting triple to cidstore:
     - If triple has `provenance["triple_hash"]`, stores `hash → JSON` in Redis
     - Uses Redis pipeline for batch insertions
     - Failures are logged as warnings but don't block cidstore writes

3. **Created example script**: `scripts/redis_integration_example.py`
   - Demonstrates Redis integration with MockCidstore
   - Shows how to verify (SHA → content) mapping

### How It Works
When `CidstoreClient` inserts a triple:
1. Triple is inserted to cidstore (primary storage)
2. If `provenance["triple_hash"]` exists (computed by `get_triple_hash()`):
   - Key: `triple_hash` (hex digest, e.g., `"deadbeefcafebabe"`)
   - Value: `triple.to_dict()` serialized as JSON bytes
3. Redis write is fire-and-forget (won't block cidstore on failure)

### Connection from cidsem
From host machine:
```python
import redis
r = redis.Redis(host='localhost', port=6379)
```

From docker container in same network:
```python
import redis
r = redis.Redis(host='redis', port=6379)
```

### Environment Variables for cidsem
If running cidsem in docker-compose, add to the service:
```yaml
environment:
  - CIDSEM_USE_REDIS=1
  - REDIS_HOST=redis
  - REDIS_PORT=6379
```

## Testing the Integration

### Quick test from host
```powershell
# Ensure redis client is installed
pip install redis

# Set environment for local testing
$env:REDIS_HOST = 'localhost'
$env:REDIS_PORT = '6379'

# Run example script
python scripts/redis_integration_example.py
```

Expected output:
- MockCidstore insert calls
- Redis write confirmation
- Retrieved value from Redis

### Integration test requirements
To write/run integration tests that use Redis:
1. Ensure docker-compose stack is running (`docker compose up -d`)
2. Install redis-py (`pip install redis`)
3. Use `REDIS_HOST=localhost` when connecting from host

## Next Steps / Future Enhancements

### Optional improvements not yet implemented:
1. **Key prefix**: Use `triple:{sha}` instead of just `{sha}` for Redis keys
2. **TTL**: Add expiration for Redis entries (e.g., 30 days)
3. **Redis JSON**: Use RedisJSON module for native JSON storage (requires redis-stack)
4. **Transactional writes**: Rollback cidstore insertion if Redis write fails (requires 2PC or saga pattern)
5. **Add cidsem service to docker-compose**: Build and run cidsem container alongside cidstore+redis

### Files to share with team
- `docker-compose.yml` — updated with new port mappings and env vars
- `Dockerfile.cidstore` — cidstore build definition
- `CIDSTORE_HANDOFF_README.md` — complete handoff documentation
- `src/cidsem/cidstore.py` — client with Redis integration
- `pyproject.toml` — includes redis dependency
- `scripts/redis_integration_example.py` — runnable demo

## Troubleshooting

### Redis connection refused
- Ensure redis container is running: `docker ps --filter name=redis`
- Check network: `docker network inspect cidsem_app-network`
- Verify `REDIS_HOST=redis` (service name, not localhost) when connecting from container

### CIDStore won't start (HDF5 lock error)
- Clear volumes: `docker compose down -v`
- Restart: `docker compose up -d`

### Redis writes failing silently
- Check logs: `docker logs cidstore | grep -i redis`
- Verify `CIDSEM_USE_REDIS=1` is set
- Test Redis directly: `docker exec redis redis-cli ping`

---

**Integration complete and verified as of November 2, 2025.**
