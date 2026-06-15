"""Cart recovery scheduler - sends recovery emails for abandoned carts."""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, exists
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session
from app.models.settings import CartRecovery
from app.models.cart import CartItem
from app.models.user import User
from app.models.order import Order
from app.services.email import send_cart_recovery_email
from app.services.sms import send_cart_recovery_sms

logger = logging.getLogger("souvenirx.tasks.cart_recovery")


async def check_abandoned_carts(ctx: dict) -> None:
    """Check for abandoned carts and send recovery emails.
    
    Only processes carts that haven't been converted to orders.
    Raises exceptions to allow ARQ retry mechanism to work.
    """
    async with async_session() as db:
        abandoned_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

        result = await db.execute(
            select(CartItem.user_id)
            .distinct()
            .where(CartItem.created_at < abandoned_threshold)
            .where(
                ~exists(
                    select(1)
                    .select_from(Order)
                    .where(Order.user_id == CartItem.user_id)
                    .where(Order.created_at >= CartItem.created_at)
                )
            )
        )
        user_ids = [row[0] for row in result.all()]

        try:
            for user_id in user_ids:
                recovery_result = await db.execute(
                    select(CartRecovery).where(CartRecovery.user_id == user_id)
                )
                recovery = recovery_result.scalar_one_or_none()

                should_send = False
                if not recovery:
                    should_send = True
                elif recovery.last_recovery_attempt:
                    days_since_last = (datetime.now(timezone.utc) - recovery.last_recovery_attempt).days
                    if days_since_last >= 7 and recovery.recovery_count < 3:
                        should_send = True

                if should_send:
                    user_result = await db.execute(select(User).where(User.id == user_id))
                    user = user_result.scalar_one_or_none()

                    if user and user.email:
                        email_sent = await send_cart_recovery_email(user.email, user.name or "Customer", db)

                        sms_sent = False
                        if user.phone:
                            sms_sent = await send_cart_recovery_sms(user.phone, user.name or "Customer")

                        if not recovery:
                            recovery = CartRecovery(
                                user_id=user_id,
                                recovery_count=1,
                                last_recovery_attempt=datetime.now(timezone.utc),
                            )
                            db.add(recovery)
                        else:
                            recovery.recovery_count += 1
                            recovery.last_recovery_attempt = datetime.now(timezone.utc)
                            if email_sent:
                                recovery.email_sent_at = datetime.now(timezone.utc)
                            if sms_sent:
                                recovery.sms_sent_at = datetime.now(timezone.utc)

                        await db.flush()
                        logger.info("Sent recovery email to %s (user_id: %s)", user.email, user_id)

            await db.commit()
            logger.info("Processed %d abandoned carts", len(user_ids))

        except SQLAlchemyError as e:
            logger.error("Database error in cart recovery: %s", e, exc_info=True)
            await db.rollback()
            raise
        except Exception as e:
            logger.error("Unexpected error in cart recovery: %s", e, exc_info=True)
            await db.rollback()
            raise
