import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.config import settings
from app.database import Base, _ensure_async_driver, _get_engine_connect_args, _strip_ssl_params_from_url
from app.models import *  # noqa: F401,F403 — import all models so Alembic sees them

# Get cleaned database URL (SSL params stripped) for Alembic
_cleaned_db_url, _ = _get_engine_connect_args()

config = context.config
config.set_main_option("sqlalchemy.url", _ensure_async_driver(_cleaned_db_url))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # Get configuration section and add SSL connect args
    configuration = config.get_section(config.config_ini_section, {})
    
    # Get SSL connection arguments to handle production SSL requirements
    # The URL is already cleaned (SSL params stripped) in the config above
    _, connect_args = _get_engine_connect_args()
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
