"""Helper for creating in-app notifications at key business events.

Every `notify_*` helper now also sends an FCM push notification
(if the user has a registered device token).
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType


async def create_notification(
    db: "AsyncSession",
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    message: str,
    link: str | None = None,
    link_text: str | None = None,
) -> Notification:
    """Insert a notification row. Does NOT commit — callers flush/commit themselves."""
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        link=link,
        link_text=link_text,
    )
    db.add(notif)
    return notif


async def _send_push(
    db: "AsyncSession",
    user_id: uuid.UUID,
    title: str,
    message: str,
    link: str | None = None,
    notification_type: str | None = None,
) -> None:
    """Fire-and-forget FCM push. Never raises — errors are logged internally."""
    try:
        from app.services.fcm_service import send_push
        data = {}
        if link:
            data["link"] = link
        if notification_type:
            data["type"] = notification_type
        await send_push(db, user_id, title=title, body=message, data=data)
    except Exception:
        pass  # Push failure must never break the calling flow


# ── Convenience wrappers for each event ──────────────────────────────────────

async def notify_order_placed(db: "AsyncSession", user_id: uuid.UUID, order_number: str) -> None:
    await create_notification(
        db, user_id,
        type=NotificationType.order_status,
        title="Order placed",
        message=f"Your order {order_number} has been received. We'll notify you when it moves into production.",
        link=f"/track?id={order_number}",
        link_text="Track order",
    )
    await _send_push(db, user_id, "Order placed",
                     f"Your order {order_number} has been received.",
                     link=f"/track?id={order_number}",
                     notification_type="order_status")


async def notify_order_cancelled(db: "AsyncSession", user_id: uuid.UUID, order_number: str) -> None:
    await create_notification(
        db, user_id,
        type=NotificationType.order_status,
        title="Order cancelled",
        message=f"Your order {order_number} has been cancelled.",
        link=f"/track?id={order_number}",
        link_text="View order",
    )
    await _send_push(db, user_id, "Order cancelled",
                     f"Your order {order_number} has been cancelled.",
                     link=f"/track?id={order_number}",
                     notification_type="order_status")


async def notify_payment_confirmed(db: "AsyncSession", user_id: uuid.UUID, order_number: str) -> None:
    await create_notification(
        db, user_id,
        type=NotificationType.payment,
        title="Payment confirmed",
        message=f"Payment for order {order_number} was successful. Your order is now in production.",
        link=f"/track?id={order_number}",
        link_text="Track order",
    )
    await _send_push(db, user_id, "Payment confirmed",
                     f"Payment for order {order_number} was successful.",
                     link=f"/track?id={order_number}",
                     notification_type="payment")


async def notify_payment_rejected(db: "AsyncSession", user_id: uuid.UUID, order_number: str) -> None:
    await create_notification(
        db, user_id,
        type=NotificationType.payment,
        title="Payment could not be verified",
        message=f"We could not verify your bank transfer for order {order_number}. Please re-upload your proof of payment or contact support.",
        link=f"/track?id={order_number}",
        link_text="View order",
    )
    await _send_push(db, user_id, "Payment could not be verified",
                     f"We could not verify payment for order {order_number}.",
                     link=f"/track?id={order_number}",
                     notification_type="payment")


async def notify_bank_transfer_received(db: "AsyncSession", user_id: uuid.UUID, order_number: str) -> None:
    await create_notification(
        db, user_id,
        type=NotificationType.payment,
        title="Bank transfer proof received",
        message=f"We've received your proof of payment for order {order_number}. Our team will verify it shortly.",
        link=f"/track?id={order_number}",
        link_text="Track order",
    )
    await _send_push(db, user_id, "Bank transfer proof received",
                     f"Proof of payment for order {order_number} received.",
                     link=f"/track?id={order_number}",
                     notification_type="payment")


async def notify_order_status_changed(
    db: "AsyncSession",
    user_id: uuid.UUID,
    order_number: str,
    new_status: str,
) -> None:
    _STATUS_COPY: dict[str, tuple[str, str]] = {
        "in_production": ("Order in production", "Your order {n} is being produced by our team."),
        "shipped":       ("Order shipped",       "Your order {n} has been dispatched and is on its way."),
        "delivered":     ("Order delivered",     "Your order {n} has been delivered. Enjoy!"),
        "cancelled":     ("Order cancelled",     "Your order {n} has been cancelled. Contact support if this was unexpected."),
        "processing":    ("Order processing",    "Your order {n} is being reviewed."),
    }
    title, msg_tpl = _STATUS_COPY.get(
        new_status,
        ("Order update", f"Your order {{n}} status changed to {new_status.replace('_', ' ')}."),
    )
    await create_notification(
        db, user_id,
        type=NotificationType.order_status,
        title=title,
        message=msg_tpl.format(n=order_number),
        link=f"/track?id={order_number}",
        link_text="Track order",
    )
    await _send_push(db, user_id, title,
                     msg_tpl.format(n=order_number),
                     link=f"/track?id={order_number}",
                     notification_type="order_status")


async def notify_affiliate_approved(db: "AsyncSession", user_id: uuid.UUID) -> None:
    await create_notification(
        db, user_id,
        type=NotificationType.system,
        title="Affiliate account approved",
        message="Your affiliate account has been approved. You can now start sharing your referral link and earning commissions.",
        link="/affiliate",
        link_text="Go to dashboard",
    )
    await _send_push(db, user_id, "Affiliate account approved",
                     "Your affiliate account has been approved.",
                     link="/affiliate",
                     notification_type="system")


async def notify_affiliate_suspended(db: "AsyncSession", user_id: uuid.UUID) -> None:
    await create_notification(
        db, user_id,
        type=NotificationType.system,
        title="Affiliate account suspended",
        message="Your affiliate account has been suspended. Please contact support for more information.",
    )
    await _send_push(db, user_id, "Affiliate account suspended",
                     "Your affiliate account has been suspended.",
                     notification_type="system")


async def notify_payout_processed(db: "AsyncSession", user_id: uuid.UUID, amount: int) -> None:
    await create_notification(
        db, user_id,
        type=NotificationType.payment,
        title="Payout processed",
        message=f"A payout of ₦{amount:,} has been processed and will arrive in your bank account within 1-3 business days.",
        link="/affiliate",
        link_text="View earnings",
    )
    await _send_push(db, user_id, "Payout processed",
                     f"A payout of ₦{amount:,} has been processed.",
                     link="/affiliate",
                     notification_type="payment")


async def notify_stock_back(db: "AsyncSession", user_id: uuid.UUID, product_name: str, product_id: str) -> None:
    """Notify a user that a product they watched is back in stock."""
    await create_notification(
        db, user_id,
        type=NotificationType.promotion,
        title="Product Back in Stock",
        message=f"{product_name} is back in stock! Order now before it sells out.",
        link=f"/products/{product_id}",
        link_text="Shop Now",
    )
    await _send_push(db, user_id, "Product Back in Stock",
                     f"{product_name} is back in stock!",
                     link=f"/products/{product_id}",
                     notification_type="promotion")
