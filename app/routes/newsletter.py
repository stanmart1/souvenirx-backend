from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.newsletter import NewsletterSubscriber

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
                # Resend verification
                return {"message": "Verification email sent again"}
        else:
            # Re-subscribe
            existing.is_subscribed = True
            existing.unsubscribed_at = None
            await db.flush()
            return {"message": "Resubscribed successfully"}
    
    # Create new subscriber
    verification_token = secrets.token_urlsafe(32)
    subscriber = NewsletterSubscriber(
        email=email,
        is_subscribed=True,
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(subscriber)
    await db.flush()
    
    # In production, send verification email via SendGrid/Mailgun
    # For now, just return success
    return {
        "message": "Subscription successful. Please check your email to verify.",
        "verification_token": verification_token,  # For testing only
    }


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
