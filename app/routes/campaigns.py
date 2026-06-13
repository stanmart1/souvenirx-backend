import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.user import User
from app.models.newsletter import NewsletterSubscriber
from app.models.email_campaign import EmailCampaign, CampaignRecipient
from app.services.email import send_email

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str
    subject: str
    html_content: str
    target_audience: str = "all"
    scheduled_at: Optional[datetime] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    html_content: Optional[str] = None
    target_audience: Optional[str] = None
    scheduled_at: Optional[datetime] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _campaign_dict(c: EmailCampaign) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "subject": c.subject,
        "status": c.status,
        "target_audience": c.target_audience,
        "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
        "sent_at": c.sent_at.isoformat() if c.sent_at else None,
        "sent_count": c.sent_count,
        "opened_count": c.opened_count,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


async def _get_campaign_or_404(campaign_id: str, db: AsyncSession) -> EmailCampaign:
    try:
        campaign_uuid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign_id")

    result = await db.execute(
        select(EmailCampaign).where(EmailCampaign.id == campaign_uuid)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/admin/campaigns")
async def list_campaigns(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all email campaigns ordered by created_at descending."""
    result = await db.execute(
        select(EmailCampaign).order_by(EmailCampaign.created_at.desc())
    )
    campaigns = result.scalars().all()
    return [_campaign_dict(c) for c in campaigns]


@router.post("/admin/campaigns", status_code=201)
async def create_campaign(
    body: CampaignCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new email campaign (status defaults to 'draft')."""
    campaign = EmailCampaign(
        name=body.name,
        subject=body.subject,
        html_content=body.html_content,
        target_audience=body.target_audience,
        scheduled_at=body.scheduled_at,
        created_by_id=admin.id,
    )
    db.add(campaign)
    await db.flush()
    return _campaign_dict(campaign)


@router.get("/admin/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a single campaign by ID."""
    campaign = await _get_campaign_or_404(campaign_id, db)
    return _campaign_dict(campaign)


@router.put("/admin/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a campaign — only allowed when status is 'draft'."""
    campaign = await _get_campaign_or_404(campaign_id, db)

    if campaign.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft campaigns can be edited",
        )

    if body.name is not None:
        campaign.name = body.name
    if body.subject is not None:
        campaign.subject = body.subject
    if body.html_content is not None:
        campaign.html_content = body.html_content
    if body.target_audience is not None:
        campaign.target_audience = body.target_audience
    if body.scheduled_at is not None:
        campaign.scheduled_at = body.scheduled_at

    campaign.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return _campaign_dict(campaign)


@router.delete("/admin/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a campaign — only allowed when status is 'draft'."""
    campaign = await _get_campaign_or_404(campaign_id, db)

    if campaign.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft campaigns can be deleted",
        )

    await db.delete(campaign)
    await db.flush()
    return {"message": "Campaign deleted"}


@router.post("/admin/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Send an email campaign to the target audience.
    - Fetches recipients based on target_audience.
    - Sends email to each recipient via send_email().
    - Updates campaign status to 'sent' (or 'failed' on error).
    """
    campaign = await _get_campaign_or_404(campaign_id, db)

    if campaign.status not in ("draft", "scheduled"):
        raise HTTPException(
            status_code=400,
            detail=f"Campaign cannot be sent (current status: {campaign.status})",
        )

    # Mark as sending
    campaign.status = "sending"
    campaign.updated_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        # ── Fetch recipients ──────────────────────────────────────────────────
        recipient_emails: list[str] = []

        if campaign.target_audience == "all":
            result = await db.execute(
                select(User.email).where(User.is_active == True)
            )
            recipient_emails = list(result.scalars().all())

        elif campaign.target_audience == "customers":
            result = await db.execute(
                select(User.email).where(
                    User.role == "customer",
                    User.is_active == True,
                )
            )
            recipient_emails = list(result.scalars().all())

        elif campaign.target_audience == "affiliates":
            result = await db.execute(
                select(User.email).where(
                    User.role.in_(["affiliate"]),
                    User.is_active == True,
                )
            )
            recipient_emails = list(result.scalars().all())

        elif campaign.target_audience == "newsletter":
            result = await db.execute(
                select(NewsletterSubscriber.email).where(
                    NewsletterSubscriber.is_verified == True
                )
            )
            recipient_emails = list(result.scalars().all())

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_emails: list[str] = []
        for email in recipient_emails:
            if email not in seen:
                seen.add(email)
                unique_emails.append(email)

        # ── Send emails ───────────────────────────────────────────────────────
        sent_count = 0
        for email in unique_emails:
            try:
                success = await send_email(
                    to=email,
                    subject=campaign.subject,
                    html=campaign.html_content,
                )
                status = "sent" if success else "failed"
                sent_at = datetime.now(timezone.utc) if success else None
                if success:
                    sent_count += 1
            except Exception as exc:
                print(f"[CAMPAIGN ERROR] Failed to send to {email}: {exc}")
                status = "failed"
                sent_at = None

            recipient = CampaignRecipient(
                campaign_id=campaign.id,
                email=email,
                status=status,
                sent_at=sent_at,
            )
            db.add(recipient)

        # ── Update campaign ───────────────────────────────────────────────────
        campaign.status = "sent"
        campaign.sent_at = datetime.now(timezone.utc)
        campaign.sent_count = sent_count
        campaign.updated_at = datetime.now(timezone.utc)
        await db.flush()

        return {"message": "Campaign sent", "sent_count": sent_count}

    except Exception as exc:
        campaign.status = "failed"
        campaign.updated_at = datetime.now(timezone.utc)
        await db.flush()
        raise HTTPException(
            status_code=500,
            detail=f"Campaign sending failed: {str(exc)}",
        )
