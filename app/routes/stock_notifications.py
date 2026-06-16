import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user, get_current_admin
from app.models.user import User
from app.models.product import Product
from app.models.stock_notification import StockNotification
from app.models.notification import Notification, NotificationType
from app.services.notifications import notify_stock_back

router = APIRouter()


# ── Request / Response schemas ───────────────────────────────────────────────

class NotifyRequest(BaseModel):
    product_id: str
    email: Optional[str] = None


# ── Public / optional-auth endpoints ─────────────────────────────────────────

@router.post("/notify")
async def subscribe_stock_notification(
    body: NotifyRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a 'notify me when back in stock' request.
    - Logged-in users: stored by user_id.
    - Guests: stored by guest_email (required if not logged in).
    """
    # Validate product_id
    try:
        product_uuid = uuid.UUID(body.product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product_id")

    # Ensure product exists
    result = await db.execute(select(Product).where(Product.id == product_uuid))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if current_user:
        # Check for duplicate (logged-in user)
        existing = await db.execute(
            select(StockNotification).where(
                StockNotification.user_id == current_user.id,
                StockNotification.product_id == product_uuid,
                StockNotification.is_notified == False,
            )
        )
        if existing.scalar_one_or_none():
            return {"message": "You are already on the notification list for this product"}

        notification = StockNotification(
            user_id=current_user.id,
            product_id=product_uuid,
        )
    else:
        # Guest flow – email is required
        if not body.email:
            raise HTTPException(
                status_code=400,
                detail="Email is required for guest notifications",
            )

        guest_email = body.email.strip().lower()

        # Check for duplicate (guest email)
        existing = await db.execute(
            select(StockNotification).where(
                StockNotification.guest_email == guest_email,
                StockNotification.product_id == product_uuid,
                StockNotification.is_notified == False,
            )
        )
        if existing.scalar_one_or_none():
            return {"message": "You are already on the notification list for this product"}

        notification = StockNotification(
            guest_email=guest_email,
            product_id=product_uuid,
        )

    db.add(notification)
    await db.flush()
    return {"message": "You'll be notified when this product is back in stock"}


@router.delete("/notify")
async def unsubscribe_stock_notification(
    product_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a logged-in user's stock notification for a product."""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product_id")

    result = await db.execute(
        select(StockNotification).where(
            StockNotification.user_id == current_user.id,
            StockNotification.product_id == product_uuid,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.flush()
    return {"message": "Stock notification removed"}


@router.get("/my-notifications")
async def list_my_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active (un-notified) stock notifications for the logged-in user."""
    result = await db.execute(
        select(StockNotification, Product.name.label("product_name"))
        .join(Product, StockNotification.product_id == Product.id)
        .where(
            StockNotification.user_id == current_user.id,
            StockNotification.is_notified == False,
        )
        .order_by(StockNotification.created_at.desc())
    )
    rows = result.all()

    return [
        {
            "id": str(row.StockNotification.id),
            "product_id": str(row.StockNotification.product_id),
            "product_name": row.product_name,
            "created_at": row.StockNotification.created_at.isoformat(),
        }
        for row in rows
    ]


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/stock-alerts")
async def list_pending_stock_alerts(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all pending stock notifications grouped by product."""
    result = await db.execute(
        select(
            StockNotification.product_id,
            Product.name.label("product_name"),
            func.count(StockNotification.id).label("pending_count"),
        )
        .join(Product, StockNotification.product_id == Product.id)
        .where(StockNotification.is_notified == False)
        .group_by(StockNotification.product_id, Product.name)
        .order_by(func.count(StockNotification.id).desc())
    )
    rows = result.all()

    return [
        {
            "product_id": str(row.product_id),
            "product_name": row.product_name,
            "pending_count": row.pending_count,
        }
        for row in rows
    ]


@router.post("/admin/stock-alerts/{product_id}/notify")
async def send_stock_notifications(
    product_id: str,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Send notifications for a specific product that is back in stock.
    - Logged-in users receive an in-app Notification.
    - Guest emails are printed (email service can be wired later).
    Marks all matching notifications as is_notified=True.
    """
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product_id")

    # Ensure product exists
    p_result = await db.execute(select(Product).where(Product.id == product_uuid))
    product = p_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Fetch all pending notifications for this product
    result = await db.execute(
        select(StockNotification).where(
            StockNotification.product_id == product_uuid,
            StockNotification.is_notified == False,
        )
    )
    pending = result.scalars().all()

    if not pending:
        return {"message": "No pending notifications for this product", "sent_count": 0}

    notified_count = 0
    for sn in pending:
        if sn.user_id:
            # Create in-app notification + push for registered users
            await notify_stock_back(db, sn.user_id, product.name, str(product.id))
        elif sn.guest_email:
            # Email service can be wired later; print for now
            print(
                f"[STOCK NOTIFY EMAIL] To: {sn.guest_email} | "
                f"Product: {product.name} is back in stock."
            )

        sn.is_notified = True
        notified_count += 1

    await db.flush()
    return {"message": "Notifications sent", "sent_count": notified_count}
