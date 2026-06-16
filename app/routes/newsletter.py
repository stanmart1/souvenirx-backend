from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.newsletter import NewsletterSubscriber
from app.services.email import send_email

router = APIRouter()


@router.post("/subscribe")
async def subscribe_newsletter(email: str, db: AsyncSession = Depends(get_db)):
    """Subscribe to newsletter with double opt-in."""
    import uuid
    import secrets
    
    # Check if already subscribed
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        if existing.is_subscribed:
            if existing.is_verified:
                return {"message": "Already subscribed and verified"}
            else:
                verify_url = f"{settings.frontend_url}/newsletter/verify?token={existing.verification_token}"
                html = (
                    f'<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">'
                    f'<h2>Confirm your SouvenirX newsletter subscription</h2>'
                    f'<p>Click the button below to verify your email:</p>'
                    f'<a href="{verify_url}" style="display:inline-block;background:#c4673a;color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;">Verify Email</a>'
                    f'<p style="color:#888;font-size:13px;margin-top:16px;">Or copy this link: {verify_url}</p>'
                    f'</div>'
                )
                await send_email(to=email, subject="Verify your SouvenirX newsletter subscription", html=html)
                return {"message": "Verification email sent again"}
        else:
            existing.is_subscribed = True
            existing.unsubscribed_at = None
            await db.flush()
            return {"message": "Resubscribed successfully"}

    verification_token = secrets.token_urlsafe(32)
    subscriber = NewsletterSubscriber(
        email=email,
        is_subscribed=True,
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(subscriber)
    await db.flush()

    verify_url = f"{settings.frontend_url}/newsletter/verify?token={verification_token}"
    html = (
        f'<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">'
        f'<h2>Welcome to the SouvenirX newsletter!</h2>'
        f'<p>Click the button below to confirm your subscription:</p>'
        f'<a href="{verify_url}" style="display:inline-block;background:#c4673a;color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;">Confirm Subscription</a>'
        f'<p style="color:#888;font-size:13px;margin-top:16px;">Or copy this link: {verify_url}</p>'
        f'</div>'
    )
    await send_email(to=email, subject="Confirm your SouvenirX newsletter subscription", html=html)

    return {"message": "Subscription successful. Please check your email to verify."}


@router.post("/verify")
async def verify_subscription(token: str, db: AsyncSession = Depends(get_db)):
    """Verify newsletter subscription."""
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.verification_token == token)
    )
    subscriber = result.scalar_one_or_none()
    
    if not subscriber:
        raise HTTPException(status_code=404, detail="Invalid verification token")
    
    subscriber.is_verified = True
    subscriber.verification_token = None
    await db.flush()
    
    return {"message": "Subscription verified successfully"}


@router.post("/unsubscribe")
async def unsubscribe_newsletter(email: str, db: AsyncSession = Depends(get_db)):
    """Unsubscribe from newsletter."""
    from datetime import datetime, timezone
    
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )
    subscriber = result.scalar_one_or_none()
    
    if not subscriber:
        raise HTTPException(status_code=404, detail="Email not found")
    
    subscriber.is_subscribed = False
    subscriber.unsubscribed_at = datetime.now(timezone.utc)
    await db.flush()
    
    return {"message": "Unsubscribed successfully"}
