from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.loyalty import LoyaltyTransaction, LoyaltyRule

router = APIRouter(prefix="/api/loyalty", tags=["Loyalty"])


async def get_rule_value(db: AsyncSession, rule_type: str) -> int | None:
    result = await db.execute(
        select(LoyaltyRule).where(
            LoyaltyRule.type == rule_type,
            LoyaltyRule.is_active == True,
        )
    )
    rule = result.scalar_one_or_none()
    return rule.value if rule else None


async def award_points(
    db: AsyncSession,
    user_id: uuid.UUID,
    points: int,
    tx_type: str,
    description: str,
    order_number: str | None = None,
    reference_id: str | None = None,
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return

    user.loyalty_points = (user.loyalty_points or 0) + points

    tx = LoyaltyTransaction(
        user_id=user_id,
        points=points,
        type=tx_type,
        description=description,
        order_number=order_number,
        reference_id=reference_id,
    )
    db.add(tx)
    await db.flush()


@router.get("/summary")
async def loyalty_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LoyaltyTransaction)
        .where(LoyaltyTransaction.user_id == user.id)
        .order_by(desc(LoyaltyTransaction.created_at))
        .limit(10)
    )
    recent = result.scalars().all()

    total_earned_result = await db.execute(
        select(func.coalesce(func.sum(LoyaltyTransaction.points), 0)).where(
            LoyaltyTransaction.user_id == user.id,
            LoyaltyTransaction.points > 0,
        )
    )
    total_earned = total_earned_result.scalar() or 0

    total_redeemed_result = await db.execute(
        select(func.coalesce(func.sum(func.abs(LoyaltyTransaction.points)), 0)).where(
            LoyaltyTransaction.user_id == user.id,
            LoyaltyTransaction.points < 0,
        )
    )
    total_redeemed = total_redeemed_result.scalar() or 0

    redeem_rate = await get_rule_value(db, "redeem_rate") or 10

    return {
        "current_points": user.loyalty_points or 0,
        "total_earned": total_earned,
        "total_redeemed": total_redeemed,
        "redeem_rate": redeem_rate,
        "redeem_value_per_point": 1 / redeem_rate if redeem_rate else 0,
        "recent_transactions": [
            {
                "id": tx.id,
                "points": tx.points,
                "type": tx.type,
                "description": tx.description,
                "order_number": tx.order_number,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in recent
        ],
    }


@router.get("/transactions")
async def loyalty_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(
        select(func.count()).where(LoyaltyTransaction.user_id == user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(LoyaltyTransaction)
        .where(LoyaltyTransaction.user_id == user.id)
        .order_by(desc(LoyaltyTransaction.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    transactions = result.scalars().all()

    return {
        "transactions": [
            {
                "id": tx.id,
                "points": tx.points,
                "type": tx.type,
                "description": tx.description,
                "order_number": tx.order_number,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in transactions
        ],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/referral-link")
async def get_referral_link(
    user: User = Depends(get_current_user),
):
    return {
        "referral_link": f"https://souvenir-x.com/ref/{user.id}",
        "referral_code": str(user.id)[:8].upper(),
    }
