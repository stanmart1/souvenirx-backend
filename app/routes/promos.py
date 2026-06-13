from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.promo import PromoCode
from app.schemas.payment import PromoValidate

router = APIRouter()


@router.post("/validate")
async def validate_promo(body: PromoValidate, db: AsyncSession = Depends(get_db)):
    code = body.code.upper().strip()
    subtotal = body.subtotal

    result = await db.execute(select(PromoCode).where(PromoCode.code == code))
    promo = result.scalar_one_or_none()

    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    if not promo.is_active:
        raise HTTPException(status_code=400, detail="Promo code is no longer active")
    if promo.expires_at and promo.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Promo code has expired")
    if promo.max_uses and promo.current_uses >= promo.max_uses:
        raise HTTPException(status_code=400, detail="Promo code usage limit reached")
    if subtotal < promo.min_order_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order amount is ₦{promo.min_order_amount:,}",
        )

    discount = int(subtotal * promo.discount_percent / 100)
    return {
        "code": promo.code,
        "discount_percent": promo.discount_percent,
        "discount_amount": discount,
    }
