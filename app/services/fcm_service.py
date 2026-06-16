"""Firebase Cloud Messaging push notification service.

Initialises the Firebase Admin SDK from the credentials file configured
in FIREBASE_CREDENTIALS_PATH and provides a single helper to send
push notifications to a user's device via their stored FCM token.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.config import settings
from app.models.user import User

logger = logging.getLogger("souvenirx")

# ── Lazy-initialised Firebase app ──────────────────────────────────────────────
_firebase_app = None


def _get_firebase_app():
    """Return the initialised Firebase app (lazy singleton)."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred_path = settings.firebase_credentials_path
    if not cred_path:
        logger.warning("FIREBASE_CREDENTIALS_PATH not set — push notifications disabled")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials as fb_creds

        cred = fb_creds.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialised (project: %s)", cred.project_id)
        return _firebase_app
    except Exception:
        logger.exception("Failed to initialise Firebase Admin SDK")
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

async def send_push(
    db: "AsyncSession",
    user_id: uuid.UUID,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> bool:
    """Send an FCM push notification to a single user.

    Returns True if the message was sent successfully (or silently skipped
    because the user has no FCM token), False on a real send failure.
    """
    app = _get_firebase_app()
    if app is None:
        return False  # Firebase not configured — skip silently

    # Look up the user's FCM token
    result = await db.execute(select(User.fcm_token).where(User.id == user_id))
    token = result.scalar_one_or_none()
    if not token:
        return True  # User hasn't registered a device — not an error

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="souvenirx_notifications",
                    click_action="FLUTTER_NOTIFICATION_CLICK",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        badge=1,
                        sound="default",
                    ),
                ),
            ),
        )
        messaging.send(message, app=app)
        logger.debug("Push sent to user %s", user_id)
        return True
    except messaging.UnregisteredError:
        # Token is stale — clear it so we don't keep retrying
        logger.info("FCM token for user %s is unregistered — clearing", user_id)
        await db.execute(
            User.__table__.update()
            .where(User.id == user_id)
            .values(fcm_token=None)
        )
        await db.flush()
        return True
    except Exception:
        logger.exception("Failed to send FCM push to user %s", user_id)
        return False


async def send_push_multicast(
    db: "AsyncSession",
    user_ids: list[uuid.UUID],
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> int:
    """Send an FCM push to multiple users. Returns the count of successful sends."""
    app = _get_firebase_app()
    if app is None or not user_ids:
        return 0

    result = await db.execute(
        select(User.id, User.fcm_token).where(User.id.in_(user_ids), User.fcm_token.isnot(None))
    )
    rows = result.all()
    if not rows:
        return 0

    tokens = [r.fcm_token for r in rows]
    sent = 0

    try:
        from firebase_admin import messaging

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="souvenirx_notifications",
                    click_action="FLUTTER_NOTIFICATION_CLICK",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(badge=1, sound="default"),
                ),
            ),
        )
        response = messaging.send_multicast(message, app=app)
        sent = response.success_count

        # Clean up unregistered tokens
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                from firebase_admin.messaging import UnregisteredError
                if isinstance(resp.exception, UnregisteredError):
                    stale_user_id = rows[idx].id
                    await db.execute(
                        User.__table__.update()
                        .where(User.id == stale_user_id)
                        .values(fcm_token=None)
                    )
        await db.flush()
    except Exception:
        logger.exception("Failed to send multicast FCM push")

    return sent
