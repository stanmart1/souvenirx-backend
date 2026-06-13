"""ARQ worker — async task queue for cron jobs and background tasks."""
import logging
import ssl as ssl_module
from urllib.parse import urlparse

from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.tasks.cart_recovery import check_abandoned_carts

logger = logging.getLogger("souvenirx.worker")


def _redis_settings() -> RedisSettings:
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


async def startup(ctx: dict) -> None:
    logger.info("ARQ worker started")


async def shutdown(ctx: dict) -> None:
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    functions = [check_abandoned_carts]
    cron_jobs = [
        cron(check_abandoned_carts, hour={0, 6, 12, 18}, minute=0),
    ]
    redis_settings = _redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 30 * 60
