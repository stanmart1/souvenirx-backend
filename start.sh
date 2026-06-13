#!/bin/bash
set -e

echo "Cleaning up old migration references..."
# Use asyncpg directly (always available since the app depends on it)
python3 -c "
import asyncio
import asyncpg
import os
import re
import ssl
from urllib.parse import urlparse, parse_qs

async def cleanup():
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

    try:
        conn = await asyncpg.connect(dsn, **kwargs)
        try:
            exists = await conn.fetchval(
                \"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')\"
            )
            if exists:
                # Remove stale old-style revision entries
                deleted = await conn.execute(
                    \"DELETE FROM alembic_version WHERE version_num IN ('001', '002')\"
                )
                print(f'Cleaned up old migration references ({deleted})')
                # Widen version_num column — default VARCHAR(32) is too short for
                # long revision IDs like '20250107_add_newsletter_subscribers' (35 chars)
                await conn.execute(
                    \"ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)\"
                )
                print('Widened alembic_version.version_num to VARCHAR(255)')
            else:
                print('alembic_version table does not exist yet, skipping cleanup')
        finally:
            await conn.close()
    except Exception as e:
        print(f'Cleanup note: {e}')

asyncio.run(cleanup())
"

echo "Running database migrations..."
alembic upgrade head

echo "Starting SouvenirX API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
