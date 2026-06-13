from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.payment_method import SavedPaymentMethod
from app.models.user import User
from app.middleware.auth import get_current_user

router = APIRouter()


@router.get("")
async def list_payment_methods(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's saved payment methods."""
    result = await db.execute(
        select(SavedPaymentMethod)
        .where(SavedPaymentMethod.user_id == user.id)
        .order_by(SavedPaymentMethod.is_default.desc(), SavedPaymentMethod.created_at.desc())
    )
    methods = result.scalars().all()
    
    return [
        {
            "id": str(m.id),
            "card_last4": m.card_last4,
            "card_brand": m.card_brand,
            "expiry_month": m.expiry_month,
            "expiry_year": m.expiry_year,
            "is_default": m.is_default,
            "payment_gateway": m.payment_gateway,
        }
        for m in methods
    ]


@router.post("")
async def save_payment_method(
    payment_token: str,
    card_last4: str,
    card_brand: str,
    expiry_month: int,
    expiry_year: int,
    payment_gateway: str = "paystack",
    set_as_default: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a payment method (tokenized by payment gateway)."""
    import uuid
    
    # If setting as default, unset other defaults
    if set_as_default:
        result = await db.execute(
            select(SavedPaymentMethod).where(
                SavedPaymentMethod.user_id == user.id,
                SavedPaymentMethod.is_default == True
            )
        )
        existing = result.scalars().all()
        for m in existing:
            m.is_default = False
    
    # Check if this card already exists
    result = await db.execute(
        select(SavedPaymentMethod).where(
            SavedPaymentMethod.user_id == user.id,
            SavedPaymentMethod.card_last4 == card_last4,
            SavedPaymentMethod.card_brand == card_brand,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing
        existing.payment_token = payment_token
        existing.expiry_month = expiry_month
        existing.expiry_year = expiry_year
        if set_as_default:
            existing.is_default = True
    else:
        # Create new
        method = SavedPaymentMethod(
            user_id=user.id,
            payment_token=payment_token,
            payment_gateway=payment_gateway,
            card_last4=card_last4,
            card_brand=card_brand,
            expiry_month=expiry_month,
            expiry_year=expiry_year,
            is_default=set_as_default or True,  # First card is default
        )
        db.add(method)
    
    await db.flush()
    return {"message": "Payment method saved successfully"}


@router.post("/{method_id}/default")
async def set_default_payment_method(
    method_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set a payment method as default."""
    import uuid
    
    # Unset all defaults
    result = await db.execute(
        select(SavedPaymentMethod).where(
            SavedPaymentMethod.user_id == user.id,
            SavedPaymentMethod.is_default == True
        )
    )
    existing = result.scalars().all()
    for m in existing:
        m.is_default = False
    
    # Set new default
    result = await db.execute(
        select(SavedPaymentMethod).where(
            SavedPaymentMethod.id == uuid.UUID(method_id),
            SavedPaymentMethod.user_id == user.id
        )
    )
    method = result.scalar_one_or_none()
    
    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    method.is_default = True
    await db.flush()
    
    return {"message": "Default payment method updated"}


@router.delete("/{method_id}")
async def delete_payment_method(
    method_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved payment method."""
    import uuid
    
    result = await db.execute(
        select(SavedPaymentMethod).where(
            SavedPaymentMethod.id == uuid.UUID(method_id),
            SavedPaymentMethod.user_id == user.id
        )
    )
    method = result.scalar_one_or_none()
    
    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    await db.delete(method)
    await db.flush()
    
    return {"message": "Payment method deleted"}
