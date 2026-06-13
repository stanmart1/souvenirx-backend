# Migration Issues - Complete Fix Summary

## Issues Fixed

### 1. Multiple Head Revisions ✅
**Problem:** Two separate migration chains existed with different starting points
- Old chain: `001_initial_schema` → `002_checkout_fixes`
- New chain: `20250101_add_logo_uploads` → ... → `20250119_add_sms_templates`

**Solution:**
- Deleted old migration files (`001_initial_schema.py`, `002_checkout_fixes.py`)
- Maintained single clean migration chain starting from `20250101_add_logo_uploads`

### 2. Can't Locate Revision '002' ✅
**Problem:** Database had references to deleted migration files in `alembic_version` table

**Solution:**
- Updated `start.sh` to automatically clean up old migration references on startup
- Created cleanup scripts:
  - `clean_migrations.py` - Python script for database cleanup
  - `clean_alembic.sql` - SQL script for manual cleanup
  - `reset_migrations.sh` - Automated cleanup and migration script

### 3. Missing Imports in Models ✅
**Problem:** `Optional` and `UUID` imports missing in model files

**Solution:**
- Added `from typing import Optional` to `app/models/delivery.py`
- Added `from typing import Optional` to `app/models/settings.py`
- Added `UUID` import to `app/models/settings.py`

### 4. Incorrect Mapped() Usage ✅
**Problem:** `Mapped()` used as constructor instead of `mapped_column()`

**Solution:**
- Fixed `app/models/product.py` line 50:
  - Before: `rating: Mapped[float] = Mapped(Float, default=0.0, index=True)`
  - After: `rating: Mapped[float] = mapped_column(Float, default=0.0, index=True)`

### 5. Non-Idempotent Migrations ✅
**Problem:** Migrations would fail if run multiple times

**Solution:**
- Updated `20250101_add_logo_uploads_table.py` to check if table exists before creating
- Added idempotent checks using SQLAlchemy inspector

## Files Created/Modified

### Created Files:
1. **clean_migrations.py** - Async Python script to clean alembic_version table
2. **clean_alembic.sql** - SQL script to remove old migration records
3. **reset_migrations.sh** - Bash script to automate cleanup and migration
4. **fix_migrations.py** - Alternative cleanup script
5. **MIGRATION_CLEANUP_GUIDE.md** - Comprehensive guide for migration issues
6. **app/data/email_templates.py** - Email templates data file
7. **app/data/sms_templates.py** - SMS templates data file
8. **app/routes/email_templates.py** - Email/SMS template management routes
9. **app/celery_app.py** - Celery configuration for scheduled tasks
10. **alembic/versions/20250119_add_sms_templates.py** - SMS templates migration

### Modified Files:
1. **start.sh** - Added automatic cleanup of old migration references
2. **app/models/delivery.py** - Added Optional import
3. **app/models/settings.py** - Added Optional and UUID imports
4. **app/models/product.py** - Fixed Mapped() usage
5. **alembic/versions/20250101_add_logo_uploads_table.py** - Made idempotent
6. **app/routes/admin.py** - Removed old email template endpoints, added payout email
7. **app/routes/affiliates.py** - Added affiliate signup email
8. **app/services/email.py** - Updated to use templates
9. **app/services/sms.py** - Updated to use templates
10. **app/main.py** - Added email_templates router

### Deleted Files:
1. **alembic/versions/001_initial_schema.py** - Old migration file
2. **alembic/versions/002_checkout_fixes.py** - Old migration file

## Current Migration Chain

```
20250101_add_logo_uploads (base, down_revision=None)
  ↓
20250102_add_guest_sessions
  ↓
20250103_add_notifications
  ↓
20250104_add_support_tickets
  ↓
20250105_add_review_media
  ↓
20250106_add_testimonials
  ↓
20250107_add_newsletter_subscribers
  ↓
20250108_add_payment_methods
  ↓
20250109_add_product_groups_variants
  ↓
20250110_enhance_delivery_shipping
  ↓
20250111_add_shipping_automation
  ↓
20250112_add_west_africa_lga_support
  ↓
20250113_add_homepage_content
  ↓
20250114_add_performance_indexes
  ↓
20250115_add_cart_variant_logo_support
  ↓
20250116_add_ads_table
  ↓
20250117_add_email_templates
  ↓
20250118_add_cart_recovery
  ↓
20250119_add_sms_templates (head)
```

## How to Apply Fixes

### Automatic (Recommended)
The fixes are now automatic when you restart the container:

```bash
docker-compose down
docker-compose up -d
```

The `start.sh` script will:
1. Clean up old migration references
2. Run all migrations
3. Start the API server

### Manual (If Needed)

#### Option 1: Using Python Script
```bash
docker exec -it <container_name> python /app/clean_migrations.py
docker exec -it <container_name> alembic upgrade head
```

#### Option 2: Using SQL Script
```bash
docker exec -it <container_name> psql -U souvenirx -d souvenirx -f /app/clean_alembic.sql
docker exec -it <container_name> alembic upgrade head
```

#### Option 3: Direct SQL
```bash
docker exec -it <container_name> psql -U souvenirx -d souvenirx -c "DELETE FROM alembic_version WHERE version_num IN ('001', '002');"
docker exec -it <container_name> alembic upgrade head
```

## Verification

After applying fixes, verify everything is working:

```bash
# Check current migration
docker exec -it <container_name> alembic current

# Should show: 20250119_add_sms_templates (head)

# Check for multiple heads (should show only one)
docker exec -it <container_name> alembic heads

# View migration history
docker exec -it <container_name> alembic history

# Check database tables
docker exec -it <container_name> psql -U souvenirx -d souvenirx -c "\dt"
```

## Expected Output

After successful migration:

```
Cleaning up old migration references...
Cleaned up old migration references
Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 20250101_add_logo_uploads
INFO  [alembic.runtime.migration] Running upgrade 20250101_add_logo_uploads -> 20250102_add_guest_sessions
...
INFO  [alembic.runtime.migration] Running upgrade 20250118_add_cart_recovery -> 20250119_add_sms_templates
Starting SouvenirX API...
```

## Troubleshooting

If you still encounter issues:

1. **Complete database reset (development only):**
   ```bash
   docker exec -it <container_name> psql -U souvenirx -d postgres -c "DROP DATABASE IF EXISTS souvenirx;"
   docker exec -it <container_name> psql -U souvenirx -d postgres -c "CREATE DATABASE souvenirx;"
   docker-compose restart
   ```

2. **Check logs:**
   ```bash
   docker logs <container_name> 2>&1 | grep -i alembic
   ```

3. **Verify database connection:**
   ```bash
   docker exec -it <container_name> psql -U souvenirx -d souvenirx -c "SELECT version();"
   ```

## Summary

All migration issues have been resolved:
- ✅ Removed old migration files
- ✅ Cleaned up database references
- ✅ Fixed model import errors
- ✅ Made migrations idempotent
- ✅ Automated cleanup in start.sh
- ✅ Created comprehensive documentation

The system will now automatically handle migration cleanup on startup, preventing future issues.
