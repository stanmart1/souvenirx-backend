#!/usr/bin/env python3
"""Clean up alembic_version table and reset to proper migration chain."""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def clean_alembic_version():
    """Remove old migration records and reset to clean state."""
    
    # Database URL - adjust if needed
    database_url = "postgresql+asyncpg://souvenirx:souvenirx_secret@db:5432/souvenirx"
    
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Check if alembic_version table exists
            result = await session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
            ))
            table_exists = result.scalar()
            
            if not table_exists:
                print("alembic_version table does not exist. Creating it...")
                await session.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY)"))
                await session.commit()
                print("Created alembic_version table")
                return
            
            # Get current versions
            result = await session.execute(text("SELECT version_num FROM alembic_version"))
            current_versions = [row[0] for row in result.all()]
            print(f"Current migrations in database: {current_versions}")
            
            # Delete all old migration records
            await session.execute(text("DELETE FROM alembic_version"))
            await session.commit()
            print("Cleared all migration records from alembic_version table")
            
            print("\nDatabase is now clean. Run 'alembic upgrade head' to apply all migrations.")
            
        except Exception as e:
            print(f"Error: {e}")
            await session.rollback()
            sys.exit(1)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clean_alembic_version())
