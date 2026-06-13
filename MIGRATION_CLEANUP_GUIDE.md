# Migration Cleanup and Reset Guide

## Problem
The database has references to old migration files (`001`, `002`) that no longer exist, causing the error:
```
FAILED: Can't locate revision identified by '002'
```

## Solution

### Option 1: Using Docker (Recommended for Production)

```bash
# 1. Clean the alembic_version table
docker exec -it <container_name> psql -U souvenirx -d souvenirx -f /app/clean_alembic.sql

# OR use Python script
docker exec -it <container_name> python /app/clean_migrations.py

# 2. Run migrations
docker exec -it <container_name> alembic upgrade head
```

### Option 2: Direct SQL (Quick Fix)

Connect to your PostgreSQL database and run:

```sql
-- Remove old migration references
DELETE FROM alembic_version WHERE version_num IN ('001', '002');

-- OR completely reset (if you want to start fresh)
DELETE FROM alembic_version;
```

Then run migrations:
```bash
alembic upgrade head
```

### Option 3: Complete Database Reset (Development Only)

**WARNING: This will delete all data!**

```bash
# Drop and recreate database
docker exec -it <container_name> psql -U souvenirx -d postgres -c "DROP DATABASE IF EXISTS souvenirx;"
docker exec -it <container_name> psql -U souvenirx -d postgres -c "CREATE DATABASE souvenirx;"

# Run all migrations
docker exec -it <container_name> alembic upgrade head
```

## Files Created

1. **clean_migrations.py** - Python script to clean alembic_version table
2. **clean_alembic.sql** - SQL script to remove old migration records
3. **reset_migrations.sh** - Bash script to automate cleanup and migration
4. **fix_migrations.py** - Alternative Python cleanup script

## Migration Chain (After Cleanup)

The current migration chain is:
```
20250101_add_logo_uploads (base)
  ↓
20250102_add_guest_sessions
  ↓
20250103_add_notifications
  ↓
... (continues through all migrations)
  ↓
20250119_add_sms_templates (head)
```

## Verification

After cleanup, verify migrations are working:

```bash
# Check current migration state
alembic current

# Check migration history
alembic history

# Check for multiple heads (should show only one)
alembic heads
```

## Idempotent Migrations

All new migrations have been updated to be idempotent (safe to run multiple times). They check if tables/columns exist before creating them.

## Troubleshooting

If you still see errors:

1. **Check database connection:**
   ```bash
   docker exec -it <container_name> psql -U souvenirx -d souvenirx -c "SELECT version();"
   ```

2. **Verify alembic_version table:**
   ```bash
   docker exec -it <container_name> psql -U souvenirx -d souvenirx -c "SELECT * FROM alembic_version;"
   ```

3. **Check migration files exist:**
   ```bash
   docker exec -it <container_name> ls -la /app/alembic/versions/
   ```

4. **View Alembic logs:**
   ```bash
   docker logs <container_name> 2>&1 | grep -i alembic
   ```
