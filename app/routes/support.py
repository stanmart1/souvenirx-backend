import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user, get_current_admin
from app.models.user import User
from app.models.support_ticket import SupportTicket, TicketStatus, TicketPriority

router = APIRouter()


@router.post("")
async def create_ticket(
    subject: str,
    message: str,
    category: str | None = None,
    attachment: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new support ticket."""
    if not subject or not message:
        raise HTTPException(status_code=400, detail="Subject and message are required")
    
    attachment_url = None
    attachment_name = None
    
    if attachment:
        # In production, upload to cloud storage
        # For now, just store the filename
        attachment_name = attachment.filename
        # TODO: Implement file upload to S3/Cloudinary
    
    ticket = SupportTicket(
        user_id=user.id,
        subject=subject,
        message=message,
        category=category,
        attachment_name=attachment_name,
        status=TicketStatus.open,
        priority=TicketPriority.medium,
    )
    db.add(ticket)
    await db.flush()
    
    return {
        "id": str(ticket.id),
        "message": "Support ticket created successfully",
        "ticket_number": str(ticket.id)[:8].upper(),
    }


@router.get("")
async def list_tickets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List support tickets for the current user."""
    result = await db.execute(
        select(SupportTicket)
        .where(SupportTicket.user_id == user.id)
        .order_by(SupportTicket.created_at.desc())
    )
    tickets = result.scalars().all()
    
    return [
        {
            "id": str(t.id),
            "subject": t.subject,
            "status": t.status,
            "priority": t.priority,
            "category": t.category,
            "created_at": t.created_at.isoformat(),
            "admin_response": t.admin_response,
            "admin_responded_at": t.admin_responded_at.isoformat() if t.admin_responded_at else None,
        }
        for t in tickets
    ]


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific support ticket."""
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID")
    
    result = await db.execute(
        select(SupportTicket).where(
            SupportTicket.id == ticket_uuid,
            SupportTicket.user_id == user.id
        )
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return {
        "id": str(ticket.id),
        "subject": ticket.subject,
        "message": ticket.message,
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category,
        "attachment_url": ticket.attachment_url,
        "attachment_name": ticket.attachment_name,
        "admin_response": ticket.admin_response,
        "admin_responded_at": ticket.admin_responded_at.isoformat() if ticket.admin_responded_at else None,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Admin request bodies
# ---------------------------------------------------------------------------

class TicketUpdateBody(BaseModel):
    status: str | None = None
    priority: str | None = None
    internal_note: str | None = None


class TicketReplyBody(BaseModel):
    message: str
    close_after: bool = False


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@router.get("/admin/tickets")
async def admin_list_tickets(
    status: str | None = None,
    priority: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: paginated list of all support tickets with user info."""
    query = select(SupportTicket)
    if status:
        query = query.where(SupportTicket.status == status)
    if priority:
        query = query.where(SupportTicket.priority == priority)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    result = await db.execute(
        query.order_by(SupportTicket.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    tickets = result.scalars().all()

    items = []
    for t in tickets:
        user_info = None
        if t.user_id:
            user_result = await db.execute(select(User).where(User.id == t.user_id))
            u = user_result.scalar_one_or_none()
            if u:
                user_info = {"email": u.email, "name": u.full_name}
        reply_count = 1 if t.admin_response else 0
        items.append({
            "id": str(t.id),
            "subject": t.subject,
            "description": t.message,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "user": user_info,
            "reply_count": reply_count,
        })

    return {
        "tickets": items,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/admin/tickets/stats")
async def admin_ticket_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: ticket counts grouped by status and priority."""
    status_rows = (await db.execute(
        select(SupportTicket.status, func.count().label("count"))
        .group_by(SupportTicket.status)
    )).all()
    priority_rows = (await db.execute(
        select(SupportTicket.priority, func.count().label("count"))
        .group_by(SupportTicket.priority)
    )).all()
    return {
        "by_status": {row.status: row.count for row in status_rows},
        "by_priority": {row.priority: row.count for row in priority_rows},
    }


@router.patch("/admin/tickets/{ticket_id}")
async def admin_update_ticket(
    ticket_id: str,
    body: TicketUpdateBody,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: update status, priority, or add an internal note to a ticket."""
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID")

    result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_uuid))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if body.status is not None:
        ticket.status = body.status
    if body.priority is not None:
        ticket.priority = body.priority
    if body.internal_note is not None:
        existing = ticket.admin_response or ""
        ticket.admin_response = f"{existing}\n--- Internal Note: {body.internal_note}".strip()
        ticket.admin_responded_at = datetime.now(timezone.utc)
        ticket.admin_responded_by = admin.id

    ticket.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Ticket updated"}


@router.post("/admin/tickets/{ticket_id}/reply")
async def admin_reply_ticket(
    ticket_id: str,
    body: TicketReplyBody,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: record a reply to a support ticket."""
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID")

    result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_uuid))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    existing = ticket.admin_response or ""
    ticket.admin_response = f"{existing}\n--- Admin Reply: {body.message}".strip()
    ticket.admin_responded_at = datetime.now(timezone.utc)
    ticket.admin_responded_by = admin.id
    ticket.status = TicketStatus.closed if body.close_after else TicketStatus.in_progress
    ticket.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Reply sent"}
