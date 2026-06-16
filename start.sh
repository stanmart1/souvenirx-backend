#!/bin/bash
set -e

echo "Running database pre-flight checks..."

# Use asyncpg directly (always available since the app depends on it)
python3 -c "
import asyncio
import asyncpg
import os
import re
import ssl
import subprocess
from urllib.parse import urlparse, parse_qs

async def preflight():
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://souvenirx:souvenirx_secret@db:5432/souvenirx')
    # Normalise to a URL asyncpg/urlparse can handle
    db_url = re.sub(r'^postgresql\+asyncpg://', 'postgresql://', db_url)
    db_url = re.sub(r'^postgres://', 'postgresql://', db_url)

    parsed = urlparse(db_url)
    qs = parse_qs(parsed.query)
    sslmode = qs.get('sslmode', ['disable'])[0]

    # Build connect kwargs; strip the query string from the DSN
    dsn = parsed._replace(query='').geturl()
    kwargs = {}
    if sslmode in ('require', 'verify-ca', 'verify-full'):
        ctx = ssl.create_default_context()
        if sslmode == 'require':
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl'] = ctx

    conn = await asyncpg.connect(dsn, **kwargs)
    try:
        # Check if alembic_version table exists
        has_alembic = await conn.fetchval(
            \"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')\"
        )

        # Check if any application tables exist (excluding system tables)
        tables = await conn.fetch(
            \"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' AND table_name != 'alembic_version'\"
        )
        has_tables = len(tables) > 0

        if not has_tables:
            # Fresh database: create schema from SQLAlchemy models and stamp head
            print('Fresh database detected. Creating schema from models...')
            subprocess.run(
                ['python3', '-c', '''
import asyncio
from app.database import Base, engine
from app.models import *
async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(create())
'''],
                check=True
            )
            print('Schema created. Stamping migration head...')
            subprocess.run(['alembic', 'stamp', 'head'], check=True)
            print('Database initialized and stamped at head.')
        elif not has_alembic:
            # Database has tables but no alembic_version (e.g. restored dump or lost tracking)
            print('Database has tables but no alembic_version. Stamping head...')
            subprocess.run(['alembic', 'stamp', 'head'], check=True)
            print('Stamped at head.')
        else:
            # Normal path: clean up old references and widen column
            deleted = await conn.execute(
                \"DELETE FROM alembic_version WHERE version_num IN ('001', '002')\"
            )
            print(f'Cleaned up old migration references ({deleted})')
            await conn.execute(
                \"ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)\"
            )
            print('Widened alembic_version.version_num to VARCHAR(255)')
    finally:
        await conn.close()

asyncio.run(preflight())
"

echo "Running database migrations..."
alembic upgrade head

echo "Starting SouvenirX API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
