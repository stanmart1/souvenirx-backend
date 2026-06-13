# Production SSL Database Connection Fix

## Problem Description

The application was experiencing a `PermissionError: [Errno 13] Permission denied` when running Alembic migrations in production. This occurred when asyncpg attempted to load SSL certificates for secure database connections.

### Error Stack Trace
```
File "/usr/local/lib/python3.12/site-packages/asyncpg/connect_utils.py", line 564, in _parse_connect_dsn_and_args
    ssl.load_verify_locations(cafile=sslrootcert)
PermissionError: [Errno 13] Permission denied
```

## Root Cause

1. **SSL Certificate Permissions**: Production database URLs often include SSL parameters (e.g., `?sslmode=require`), which causes asyncpg to load system SSL certificates from `/etc/ssl/certs/ca-certificates.crt`.

2. **Docker User Permissions**: The application runs as a non-root user (`appuser`) for security, but this user didn't have read permissions on the SSL certificate files.

3. **Timing Issue**: The original Dockerfile attempted to fix permissions in the entrypoint script, but this happened after the user switch, making it ineffective.

## Solution Implemented

### 1. Dockerfile Changes (`Dockerfile`)

**Build-time Permission Fix:**
```dockerfile
# Fix SSL certificate permissions at build time
# CA certificates are public trust anchors and should be world-readable
RUN chmod -R a+r /etc/ssl/certs 2>/dev/null || true && \
    chmod a+r /etc/ssl/certs/ca-certificates.crt 2>/dev/null || true
```

**Runtime Permission Maintenance:**
The entrypoint script also ensures permissions remain correct in case they're overridden:
```bash
chmod -R a+r /etc/ssl/certs 2>/dev/null || true
chmod a+r /etc/ssl/certs/ca-certificates.crt 2>/dev/null || true
```

### 2. Database Connection Handling (`app/database.py`)

Added `_get_engine_connect_args()` function that:
- Detects SSL parameters in the DATABASE_URL
- Creates a proper SSL context with fallback handling
- Configures verification mode based on the SSL requirements
- Prevents permission errors by using Python's SSL context

**Key Features:**
- Automatic SSL detection from connection string
- Proper SSL context creation with system CA certificates
- Configurable verification modes (CERT_NONE for `sslmode=require`, CERT_REQUIRED for `sslmode=verify-*`)
- Graceful fallback if SSL parameters are not present

### 3. Alembic Migration Support (`alembic/env.py`)

Updated to use the same SSL handling:
- Imports `_get_engine_connect_args` from `app.database`
- Passes SSL connection arguments to the async engine
- Ensures migrations work in production with SSL-enabled databases

## Configuration

### Environment Variables

For production deployments with SSL-enabled PostgreSQL:

```bash
# Basic SSL (no certificate verification)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?sslmode=require

# SSL with certificate verification
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?sslmode=verify-full

# SSL preferred (falls back to non-SSL if unavailable)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?sslmode=prefer
```

### SSL Modes Supported

- `sslmode=disable` - No SSL (not recommended for production)
- `sslmode=prefer` - Try SSL, fall back to non-SSL
- `sslmode=require` - Require SSL, but don't verify certificates
- `sslmode=verify-ca` - Require SSL and verify CA certificate
- `sslmode=verify-full` - Require SSL and verify hostname

## Testing

### Local Testing with Docker

1. **Build the image:**
   ```bash
   docker build -t souvenirx-backend .
   ```

2. **Run with SSL-enabled database:**
   ```bash
   docker run -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db?sslmode=require" souvenirx-backend
   ```

3. **Verify migrations run successfully:**
   The container should start and run `alembic upgrade head` without permission errors.

### Production Deployment

1. **Rebuild the Docker image** with the updated Dockerfile
2. **Deploy the new image** to your production environment
3. **Ensure DATABASE_URL** includes appropriate SSL parameters
4. **Monitor logs** for successful database connections and migrations

## Verification

After deployment, verify the fix by:

1. **Check container logs** for successful migration:
   ```
   Running database migrations...
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   Starting SouvenirX API...
   ```

2. **Verify SSL connection** in application logs (no permission errors)

3. **Test database connectivity** through the API health endpoint:
   ```bash
   curl https://your-api-domain.com/api/health
   ```

## Security Notes

- CA certificates in `/etc/ssl/certs/` are **public trust anchors** and should be world-readable
- Making them readable doesn't expose secrets or compromise security
- The application still runs as non-root user (`appuser`) for security
- SSL verification modes can be adjusted based on your security requirements

## Rollback Plan

If issues occur:

1. **Revert to previous image** version
2. **Temporarily disable SSL** by removing SSL parameters from DATABASE_URL
3. **Investigate specific SSL configuration** requirements for your database provider

## Future Improvements

Consider these enhancements:

1. **Custom CA certificates**: Support for custom CA certificate paths via environment variable
2. **SSL configuration validation**: Add startup checks to verify SSL configuration
3. **Metrics**: Add monitoring for SSL connection failures
4. **Documentation**: Update deployment guides with SSL best practices

## Related Files

- `Dockerfile` - Container build configuration with SSL permission fixes
- `app/database.py` - Database engine creation with SSL support
- `alembic/env.py` - Migration runner with SSL support
- `.env.example` - Environment variable examples (update with SSL examples)

## Support

For issues related to this fix:
1. Check container logs for specific error messages
2. Verify DATABASE_URL format and SSL parameters
3. Ensure the Docker image was rebuilt after applying changes
4. Check database provider's SSL requirements and documentation
