"""Shared Redis configuration for ARQ worker and queue."""
import ssl as ssl_module
from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.config import settings


def get_redis_settings() -> RedisSettings:
    """
    Parse Redis URL and return RedisSettings for ARQ.
    
    Uses the same SSL configuration logic as app.redis.build_redis_ssl_context()
    to ensure consistent SSL handling across the application.
    """
    parsed = urlparse(settings.redis_url)
    database = int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0
    use_ssl = parsed.scheme == "rediss"
    ssl_ctx = None
    
    if use_ssl:
        # Map config string to ssl.CERT_* constants
        cert_reqs_map = {
            "none": ssl_module.CERT_NONE,
            "optional": ssl_module.CERT_OPTIONAL,
            "required": ssl_module.CERT_REQUIRED,
        }
        cert_reqs = cert_reqs_map.get(
            settings.redis_ssl_cert_reqs.lower(), 
            ssl_module.CERT_REQUIRED
        )
        
        # Create SSL context with proper verification settings
        ssl_ctx = ssl_module.create_default_context()
        ssl_ctx.check_hostname = cert_reqs == ssl_module.CERT_REQUIRED
        ssl_ctx.verify_mode = cert_reqs
        
        # Load CA certificates if provided
        if settings.redis_ssl_ca_certs:
            ssl_ctx.load_verify_locations(settings.redis_ssl_ca_certs)
        elif cert_reqs != ssl_module.CERT_NONE:
            # Try to load default system certificates
            try:
                ssl_ctx.load_default_certs()
            except Exception:
                # If loading default certs fails, continue anyway
                pass
        
        # Load client certificate if provided
        if settings.redis_ssl_certfile:
            ssl_ctx.load_cert_chain(
                certfile=settings.redis_ssl_certfile,
                keyfile=settings.redis_ssl_keyfile or None,
            )
    
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
        ssl=ssl_ctx,
    )
