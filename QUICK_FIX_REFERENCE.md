# Quick Reference - Production SSL Fix

## 🚨 Problem
```
PermissionError: [Errno 13] Permission denied
```
When running `alembic upgrade head` in production with SSL-enabled database.

## ✅ Solution Applied

### Files Changed
1. **Dockerfile** - Fixed SSL cert permissions
2. **app/database.py** - Added SSL context handling
3. **alembic/env.py** - Applied SSL config to migrations
4. **.env.example** - Added SSL examples

## 🚀 Quick Deploy

```bash
# 1. Rebuild image
docker build -t souvenirx-backend:latest .

# 2. Update DATABASE_URL (add SSL parameter)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?sslmode=require

# 3. Deploy
docker-compose up -d backend

# 4. Verify
docker logs souvenirx-backend | grep -i "error\|ssl"
```

## 🔍 Verify Success

```bash
# Should see:
# ✅ "Running database migrations..."
# ✅ "Starting SouvenirX API..."
# ❌ NO permission errors
# ❌ NO SSL errors

docker logs souvenirx-backend -f
```

## 🔄 Rollback (if needed)

```bash
# Quick rollback to previous version
docker pull your-registry/souvenirx-backend:v1.0.0
docker-compose down backend
docker-compose up -d backend
```

## 📚 Full Documentation

- **Technical Details:** `PRODUCTION_SSL_FIX.md`
- **Deployment Guide:** `DEPLOYMENT_CHECKLIST.md`
- **All Changes:** `CHANGES_SUMMARY.md`

## 💡 SSL Modes

```bash
# Most common (recommended)
?sslmode=require

# Most secure
?sslmode=verify-full

# Development only
?sslmode=prefer
```

## ⚠️ Important Notes

- **MUST rebuild Docker image** for fix to work
- **MUST add SSL parameter** to production DATABASE_URL
- **Test in staging first** before production
- **Keep previous image** for quick rollback

## 🆘 Troubleshooting

**Still seeing permission errors?**
- Verify new image deployed: `docker inspect souvenirx-backend | grep Image`
- Check SSL certs exist: `docker exec souvenirx-backend ls -la /etc/ssl/certs/`

**Connection refused?**
- Verify database supports SSL
- Check DATABASE_URL has correct SSL parameter
- Confirm firewall allows SSL connections

**Need help?**
- Check logs: `docker logs souvenirx-backend -f`
- Review: `PRODUCTION_SSL_FIX.md` troubleshooting section
- Contact DevOps team
