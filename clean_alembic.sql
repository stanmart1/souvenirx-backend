-- Clean up alembic_version table to remove old migration references
-- This script should be run in the PostgreSQL database

-- Step 1: Show current migration state
SELECT 'Current migrations:' as info;
SELECT version_num FROM alembic_version;

-- Step 2: Delete all old migration records
DELETE FROM alembic_version WHERE version_num IN ('001', '002');

-- Step 3: Clear all migration records to start fresh
-- Uncomment the line below if you want to completely reset migrations
-- DELETE FROM alembic_version;

-- Step 4: Verify cleanup
SELECT 'After cleanup:' as info;
SELECT version_num FROM alembic_version;

-- If the table is now empty, you can run: alembic upgrade head
-- to apply all migrations from scratch
