# Production Deployment Checklist - SSL Fix

## Pre-Deployment Verification

- [x] **Code Changes Verified**
  - [x] `Dockerfile` - SSL certificate permissions fixed at build time and runtime
  - [x] `app/database.py` - SSL connection handling with proper context
  - [x] `alembic/env.py` - Migration support for SSL connections
  - [x] `.env.example` - Updated with SSL configuration examples
  - [x] Python syntax validated (no compilation errors)

- [ ] **Environment Configuration**
  - [ ] Verify production `DATABASE_URL` includes SSL parameters (e.g., `?sslmode=require`)
  - [ ] Confirm database provider supports SSL connections
  - [ ] Check if custom CA certificates are needed (most cloud providers don't require this)

## Deployment Steps

### 1. Build New Docker Image

```bash
cd souvenirx-backend
docker build -t souvenirx-backend:ssl-fix .
```

**Expected output:**
- Build completes successfully
- No permission errors during build
- SSL certificate permissions set correctly

### 2. Tag for Production

```bash
# Tag with version and latest
docker tag souvenirx-backend:ssl-fix your-registry/souvenirx-backend:v1.1.0
docker tag souvenirx-backend:ssl-fix your-registry/souvenirx-backend:latest
```

### 3. Push to Registry

```bash
docker push your-registry/souvenirx-backend:v1.1.0
docker push your-registry/souvenirx-backend:latest
```

### 4. Update Production Environment Variables

Ensure your production environment has the correct `DATABASE_URL`:

```bash
# Example for managed PostgreSQL with SSL
DATABASE_URL=postgresql+asyncpg://user:password@db-host.provider.com:5432/souvenirx?sslmode=require
```

**Common Cloud Provider SSL Modes:**
- **AWS RDS**: `?sslmode=require`
- **Google Cloud SQL**: `?sslmode=require`
- **Azure Database**: `?sslmode=require`
- **DigitalOcean**: `?sslmode=require`
- **Heroku**: `?sslmode=require`
- **Supabase**: `?sslmode=require`
- **Neon**: `?sslmode=require`

### 5. Deploy to Production

```bash
# Pull latest image
docker pull your-registry/souvenirx-backend:latest

# Stop old container
docker stop souvenirx-backend

# Remove old container
docker rm souvenirx-backend

# Start new container
docker run -d \
  --name souvenirx-backend \
  --env-file .env.production \
  -p 8000:8000 \
  -v upload_data:/app/uploads \
  your-registry/souvenirx-backend:latest
```

**Or with Docker Compose:**
```bash
docker-compose -f docker-compose.coolify.yml pull backend
docker-compose -f docker-compose.coolify.yml up -d backend
```

## Post-Deployment Verification

### 1. Check Container Logs

```bash
docker logs souvenirx-backend -f
```

**Expected output:**
```
Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> xxxxx, migration name
Starting SouvenirX API...
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Should NOT see:**
- `PermissionError: [Errno 13] Permission denied`
- SSL certificate loading errors
- Database connection failures

### 2. Test Health Endpoint

```bash
curl https://your-api-domain.com/api/health
```

**Expected response:**
```json
{"status": "healthy"}
```

### 3. Verify Database Connection

```bash
# Check if migrations ran successfully
docker exec souvenirx-backend alembic current
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
xxxxx (head)
```

### 4. Monitor Application Logs

Watch for any SSL-related errors for the first 5-10 minutes:

```bash
docker logs souvenirx-backend -f | grep -i "ssl\|permission\|error"
```

### 5. Test Critical Endpoints

```bash
# Test authentication
curl -X POST https://your-api-domain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'

# Test database read
curl https://your-api-domain.com/api/products

# Test database write (if applicable)
# ... your specific endpoints
```

## Rollback Plan

If issues occur:

### Quick Rollback

```bash
# Revert to previous image version
docker pull your-registry/souvenirx-backend:v1.0.0
docker stop souvenirx-backend
docker rm souvenirx-backend
docker run -d \
  --name souvenirx-backend \
  --env-file .env.production \
  -p 8000:8000 \
  -v upload_data:/app/uploads \
  your-registry/souvenirx-backend:v1.0.0
```

### Temporary SSL Bypass (Emergency Only)

If you need to temporarily disable SSL while investigating:

```bash
# Update DATABASE_URL to remove SSL requirement
# Change: ?sslmode=require
# To: ?sslmode=prefer (or remove SSL parameter entirely)
```

**Note:** Only use this as a temporary measure. SSL should be enabled in production.

## Troubleshooting

### Issue: Still seeing permission errors

**Solution:**
1. Verify the new image was actually deployed: `docker inspect souvenirx-backend | grep Image`
2. Check if custom CA certificates are required by your database provider
3. Verify SSL certificate files exist: `docker exec souvenirx-backend ls -la /etc/ssl/certs/ca-certificates.crt`

### Issue: SSL connection refused

**Solution:**
1. Verify database provider supports SSL connections
2. Check if firewall rules allow SSL connections
3. Confirm DATABASE_URL has correct SSL parameters
4. Test connection from container: `docker exec souvenirx-backend curl -v https://your-db-host:5432`

### Issue: Certificate verification failed

**Solution:**
1. Use `sslmode=require` instead of `sslmode=verify-full` (doesn't verify hostname)
2. Check if database provider requires custom CA certificates
3. Verify system time is correct (certificate validation depends on it)

### Issue: Migrations fail but app works

**Solution:**
1. Check if `alembic/env.py` was updated correctly
2. Verify `_get_engine_connect_args` is imported properly
3. Run migrations manually: `docker exec souvenirx-backend alembic upgrade head`

## Success Criteria

- [ ] Container starts without errors
- [ ] Database migrations complete successfully
- [ ] No SSL or permission errors in logs
- [ ] Health endpoint returns 200 OK
- [ ] All critical API endpoints functional
- [ ] No increase in error rates (check monitoring)
- [ ] Application performance unchanged

## Monitoring

After deployment, monitor these metrics for 24-48 hours:

- **Error rates**: Should not increase
- **Response times**: Should remain consistent
- **Database connection pool**: Should be healthy
- **SSL handshake failures**: Should be zero
- **Memory usage**: Should remain stable

## Documentation Updated

- [x] `PRODUCTION_SSL_FIX.md` - Comprehensive fix documentation
- [x] `DEPLOYMENT_CHECKLIST.md` - This deployment guide
- [x] `.env.example` - SSL configuration examples
- [ ] Internal wiki/docs (if applicable)
- [ ] Team notification sent

## Sign-off

- [ ] Changes reviewed by: _______________
- [ ] Deployed by: _______________
- [ ] Deployment date: _______________
- [ ] Verified by: _______________
- [ ] Verification date: _______________

## Notes

Add any deployment-specific notes here:

---

**Related Documentation:**
- See `PRODUCTION_SSL_FIX.md` for detailed technical explanation
- See `.env.example` for configuration examples
- See `docker-compose.coolify.yml` for deployment configuration
