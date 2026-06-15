"""Shared Redis configuration for ARQ worker and queue."""
import ssl as ssl_module
from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.config import settings


def get_redis_settings() -> RedisSettings:
    """Parse Redis URL and return RedisSettings for ARQ."""
    parsed = urlparse(settings.redis_url)
    database = int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0
    use_ssl = parsed.scheme == "rediss"
    ssl_ctx = None
    if use_ssl:
        ssl_ctx = ssl_module.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl_module.CERT_NONE
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
        ssl=ssl_ctx,
    )
