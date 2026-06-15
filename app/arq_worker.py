"""ARQ worker — async task queue for cron jobs and background tasks."""
import logging

from arq import cron

from app.tasks.redis_config import get_redis_settings
from app.tasks.cart_recovery import check_abandoned_carts

logger = logging.getLogger("souvenirx.worker")


async def startup(ctx: dict) -> None:
    logger.info("ARQ worker started")


async def shutdown(ctx: dict) -> None:
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    functions = [check_abandoned_carts]
    cron_jobs = [
        cron(check_abandoned_carts, hour={0, 6, 12, 18}, minute=0),
    ]
    redis_settings = get_redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 30 * 60
