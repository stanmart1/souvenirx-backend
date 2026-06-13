import uuid
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.affiliate import Affiliate, AffiliateClick, AffiliateConversion, AffiliatePayout, AffiliateStatus

router = APIRouter()


@router.post("/register")
async def register_affiliate(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.settings import get_bool_setting
    
    # Check if affiliate requires email verification
    require_verification = await get_bool_setting(db, "affiliate_require_email_verification", True)
    if require_verification and not user.email_verified:
        raise HTTPException(
            status_code=400, 
            detail="Please verify your email address before registering as an affiliate"
        )
    
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already registered as affiliate")

    # Check if auto-approve is enabled
    auto_approve = await get_bool_setting(db, "affiliate_auto_approve", False)
    initial_status = AffiliateStatus.active.value if auto_approve else AffiliateStatus.pending.value
    
    code = secrets.token_urlsafe(6).upper()
    affiliate = Affiliate(user_id=user.id, referral_code=code, status=initial_status)
    db.add(affiliate)
    await db.flush()
    
    # Send affiliate signup email
    from app.services.email import send_affiliate_signup_email
    await send_affiliate_signup_email(user.email, user.full_name or "Affiliate", db)
    
    message = "Affiliate account activated!" if auto_approve else "Affiliate registration submitted for review"
    
    return {"referral_code": code, "status": initial_status, "message": message}


@router.get("/me")
async def get_affiliate_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not an affiliate")

    # Count clicks
    clicks_result = await db.execute(
        select(func.count()).where(AffiliateClick.affiliate_id == affiliate.id)
    )
    total_clicks = clicks_result.scalar()

    # Count conversions
    conv_result = await db.execute(
        select(func.count()).where(AffiliateConversion.affiliate_id == affiliate.id)
    )
    total_conversions = conv_result.scalar()

    return {
        "id": str(affiliate.id),
        "referral_code": affiliate.referral_code,
        "status": affiliate.status,
        "commission_rate": affiliate.commission_rate,
        "total_earnings": affiliate.total_earnings,
        "clicks": total_clicks,
        "conversions": total_conversions,
        "cookie_days": affiliate.cookie_days,
        "bank_name": affiliate.bank_name,
        "account_number": affiliate.account_number,
        "account_name": affiliate.account_name,
    }


@router.put("/me/bank-details")
async def update_bank_details(
    bank_name: str,
    account_number: str,
    account_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update affiliate bank account details for payouts"""
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not an affiliate")

    affiliate.bank_name = bank_name
    affiliate.account_number = account_number
    affiliate.account_name = account_name
    
    await db.commit()
    return {"message": "Bank details updated successfully"}


@router.get("/me/referrals")
async def list_referrals(
    page: int = 1,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not an affiliate")

    conv_result = await db.execute(
        select(AffiliateConversion)
        .where(AffiliateConversion.affiliate_id == affiliate.id)
        .order_by(AffiliateConversion.created_at.desc())
    )
    conversions = conv_result.scalars().all()
    return [
        {
            "date": c.created_at.strftime("%Y-%m-%d"),
            "order_id": str(c.order_id),
            "commission": c.commission_amount,
            "status": c.status,
        }
        for c in conversions
    ]


@router.get("/me/payouts")
async def list_payouts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not an affiliate")

    payout_result = await db.execute(
        select(AffiliatePayout)
        .where(AffiliatePayout.affiliate_id == affiliate.id)
        .order_by(AffiliatePayout.created_at.desc())
    )
    payouts = payout_result.scalars().all()
    return [
        {
            "date": p.created_at.strftime("%Y-%m-%d"),
            "amount": p.amount,
            "method": p.method,
            "status": p.status,
        }
        for p in payouts
    ]


@router.post("/me/request-payout")
async def request_payout(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not an affiliate")

    payout = AffiliatePayout(affiliate_id=affiliate.id, amount=affiliate.total_earnings)
    db.add(payout)
    await db.flush()
    return {"message": "Payout request submitted", "amount": affiliate.total_earnings}


@router.get("/track")
async def track_click(request: Request, ref: str, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Affiliate).where(Affiliate.referral_code == ref, Affiliate.status == AffiliateStatus.active.value))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        return {"status": "unknown_referral"}

    click = AffiliateClick(
        affiliate_id=affiliate.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        landing_page=request.headers.get("referer"),
    )
    db.add(click)
    await db.flush()

    response.set_cookie("svx_ref", ref, max_age=30 * 24 * 60 * 60, httponly=True, samesite="lax")
    return {"status": "tracked"}
