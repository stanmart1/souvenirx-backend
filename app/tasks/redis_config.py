"""Shared Redis configuration for ARQ worker and queue."""
from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.config import settings


def get_redis_settings() -> RedisSettings:
    """
    Parse Redis URL and return RedisSettings for arq 0.26+.

    redis-py 5.x / arq 0.26 note:
      arq passes its RedisSettings fields directly to redis.asyncio.Redis()
      which forwards them to SSLConnection.__init__().  SSLConnection does
      NOT accept 'ssl' or 'ssl_context' kwargs — passing an SSLContext
      object via ssl= causes:
          TypeError: AbstractConnection.__init__() got an unexpected
                     keyword argument 'ssl'
      The correct approach is to use arq's individual ssl_* fields
      (ssl_cert_reqs, ssl_ca_certs, etc.) which map 1-to-1 to the
      SSLConnection parameters that redis-py's RedisSSLContext accepts.

    For self-signed certificates set the env var:
        REDIS_SSL_CERT_REQS=none
    """
    parsed = urlparse(settings.redis_url)
    database = int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0
    use_ssl = parsed.scheme == "rediss"

    if not use_ssl:
        return RedisSettings(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            database=database,
            password=parsed.password,
            ssl=False,
        )

    # ssl=True tells arq/redis-py to use SSLConnection.
    # Individual ssl_* params control verification behaviour.
    # For self-signed certs: REDIS_SSL_CERT_REQS=none disables cert checking.
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
        ssl=True,
        ssl_cert_reqs=settings.redis_ssl_cert_reqs.lower(),
        ssl_ca_certs=settings.redis_ssl_ca_certs or None,
        ssl_certfile=settings.redis_ssl_certfile or None,
        ssl_keyfile=settings.redis_ssl_keyfile or None,
    )
