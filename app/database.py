import ssl
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _ensure_async_driver(url: str) -> str:
    """Convert postgres:// or postgresql:// to postgresql+asyncpg://."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _strip_ssl_params_from_url(url: str) -> str:
    """
    Remove SSL parameters from database URL.
    
    We handle SSL through connect_args instead of URL parameters
    to avoid asyncpg trying to load certificate files directly.
    """
    import re
    # Remove common SSL parameters from query string
    url = re.sub(r'[?&]sslmode=[^&]*', '', url)
    url = re.sub(r'[?&]ssl=[^&]*', '', url)
    url = re.sub(r'[?&]sslrootcert=[^&]*', '', url)
    url = re.sub(r'[?&]sslcert=[^&]*', '', url)
    url = re.sub(r'[?&]sslkey=[^&]*', '', url)
    # Clean up any trailing ? or & from removed params
    url = re.sub(r'[?&]$', '', url)
    return url


def _get_engine_connect_args() -> tuple[str, dict]:
    """
    Get database URL and connection arguments for asyncpg engine.
    
    Handles SSL configuration properly to avoid permission errors.
    If the DATABASE_URL contains SSL parameters (sslmode, ssl=true, etc.),
    we strip them from the URL and configure SSL through connect_args instead.
    This prevents asyncpg from trying to load certificate files directly.
    
    Returns:
        tuple: (cleaned_url, connect_args)
    """
    connect_args = {}
    db_url = settings.database_url
    db_url_lower = db_url.lower()
    
    # Check if SSL is required in the connection string
    has_ssl = any(param in db_url_lower for param in [
        'sslmode=require', 'sslmode=verify', 'ssl=true', 'sslmode=prefer',
        'sslmode=allow', 'sslmode=disable'
    ])
    
    if has_ssl:
        # Strip SSL parameters from URL to prevent asyncpg from parsing them
        cleaned_url = _strip_ssl_params_from_url(db_url)
        
        # Only configure SSL if not explicitly disabled
        if 'sslmode=disable' not in db_url_lower:
            # Create SSL context that doesn't require certificate files
            ssl_context = ssl.create_default_context(cafile=None)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connect_args['ssl'] = ssl_context
        
        return cleaned_url, connect_args
    
    return db_url, connect_args


# Get cleaned URL and SSL connect args
_db_url, _connect_args = _get_engine_connect_args()

engine = create_async_engine(
    _ensure_async_driver(_db_url),
    echo=False,
    pool_size=20,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args=_connect_args
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
