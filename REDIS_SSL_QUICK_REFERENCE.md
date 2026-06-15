# Redis SSL Configuration - Quick Reference

## Common Scenarios

### 1️⃣ Production with Valid SSL Certificate (Most Common)
```bash
# .env
REDIS_URL=rediss://user:password@redis.example.com:6380/0
REDIS_SSL_CERT_REQS=required
```
✅ Uses system CA certificates  
✅ Full SSL verification  
✅ Most secure  

---

### 2️⃣ Production with Self-Signed Certificate
```bash
# .env
REDIS_URL=rediss://user:password@redis.example.com:6380/0
REDIS_SSL_CERT_REQS=required
REDIS_SSL_CA_CERTS=/app/certs/redis-ca.pem
```
✅ Verifies against custom CA  
✅ Secure for internal infrastructure  

**Docker:**
```yaml
volumes:
  - ./certs:/app/certs:ro
```

---

### 3️⃣ Development with Self-Signed Certificate (Insecure)
```bash
# .env
REDIS_URL=rediss://localhost:6380/0
REDIS_SSL_CERT_REQS=none
```
⚠️ **Development only!**  
❌ Disables SSL verification  
❌ Never use in production  

---

### 4️⃣ Local Development (No SSL)
```bash
# .env
REDIS_URL=redis://localhost:6379/0
```
✅ Simple local setup  
✅ No SSL configuration needed  

---

### 5️⃣ Mutual TLS (Client Certificate)
```bash
# .env
REDIS_URL=rediss://user:password@redis.example.com:6380/0
REDIS_SSL_CERT_REQS=required
REDIS_SSL_CA_CERTS=/app/certs/redis-ca.pem
REDIS_SSL_CERTFILE=/app/certs/client.pem
REDIS_SSL_KEYFILE=/app/certs/client-key.pem
```
✅ Highest security  
✅ Both server and client authenticated  

---

## Troubleshooting

### Error: "certificate verify failed: self-signed certificate"
**Fix:** Add CA certificate
```bash
REDIS_SSL_CA_CERTS=/path/to/ca-cert.pem
```

**Or (dev only):** Disable verification
```bash
REDIS_SSL_CERT_REQS=none
```

---

### Error: "certificate verify failed: unable to get local issuer certificate"
**Fix:** Provide CA certificate chain
```bash
REDIS_SSL_CA_CERTS=/path/to/ca-bundle.pem
```

---

### Error: "Connection refused"
**Check:**
1. Redis is running: `redis-cli ping`
2. Port is correct (6379 for redis://, 6380 for rediss://)
3. Firewall allows connection
4. Host is reachable: `telnet redis-host 6380`

---

### Worker connects but API doesn't (or vice versa)
**Fix:** Both now use the same config - verify `.env` is loaded:
```bash
python -c "from app.config import settings; print(settings.redis_ssl_cert_reqs)"
```

---

## Testing

### Test ARQ Worker
```bash
python -m arq app.arq_worker.WorkerSettings
# Should see: ARQ worker started
```

### Test API
```bash
uvicorn app.main:app --reload
# Should start without Redis errors
```

### Test Redis Connection
```bash
redis-cli -h <host> -p <port> --tls
# Should connect successfully
```

---

## Security Levels

| Config | Security | Use Case |
|--------|----------|----------|
| `CERT_REQUIRED` + system CAs | 🔒🔒🔒 High | Production with valid certs |
| `CERT_REQUIRED` + custom CA | 🔒🔒 Medium-High | Production with self-signed |
| `CERT_OPTIONAL` | 🔒 Low | Testing only |
| `CERT_NONE` | ❌ None | Development only |
| No SSL (`redis://`) | ❌ None | Local development only |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | ✅ Yes | - | Redis connection URL |
| `REDIS_SSL_CERT_REQS` | ❌ No | `required` | SSL verification mode |
| `REDIS_SSL_CA_CERTS` | ❌ No | - | Path to CA certificate |
| `REDIS_SSL_CERTFILE` | ❌ No | - | Path to client certificate |
| `REDIS_SSL_KEYFILE` | ❌ No | - | Path to client key |

---

## Quick Commands

```bash
# Check current config
grep REDIS .env

# Test import
python -c "from app.tasks.redis_config import get_redis_settings; print('OK')"

# Start worker
python -m arq app.arq_worker.WorkerSettings

# Start API
uvicorn app.main:app --reload

# Test Redis connection
redis-cli -h <host> -p <port> --tls ping
```

---

## Files to Check

- ✅ `.env` - Your environment variables
- ✅ `.env.example` - Template with documentation
- ✅ `app/tasks/redis_config.py` - Worker Redis config
- ✅ `app/redis.py` - API Redis config
- ✅ `app/config.py` - Settings schema

---

**Need more details?** See `ARQ_WORKER_REDIS_SSL_FIX.md`
