#!/usr/bin/env python3
"""Fix Alembic migration chain by removing old migrations from database."""

import asyncio
from sqlalchemy import text
from app.database import get_db


async def fix_migration_chain():
    """Remove old migration records from alembic_version table."""
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # Check current migrations in database
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        current_versions = [row[0] for row in result.all()]
        print(f"Current migrations in database: {current_versions}")
        
        # Remove old migration records if they exist
        old_migrations = ['001', '002']
        for old_mig in old_migrations:
            if old_mig in current_versions:
                await db.execute(text("DELETE FROM alembic_version WHERE version_num = :ver"), {"ver": old_mig})
                print(f"Removed old migration: {old_mig}")
        
        # Check if we need to set the current version
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        remaining = [row[0] for row in result.all()]
        
        if not remaining:
            # Set to the latest migration in the new chain
            latest = '20250119_add_sms_templates'
            await db.execute(text("INSERT INTO alembic_version (version_num) VALUES (:ver)"), {"ver": latest})
            print(f"Set current version to: {latest}")
        else:
            print(f"Remaining migrations: {remaining}")
        
        await db.commit()
        print("Migration chain fixed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        await db.rollback()
    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    asyncio.run(fix_migration_chain())
