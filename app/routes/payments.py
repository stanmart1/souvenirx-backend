import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.config import settings
from app.middleware.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.order import Order, OrderStatus, PaymentStatus, PaymentGateway
from app.models.order import OrderTracking
from app.models.bank_account import BankAccount
from app.services.email import send_order_confirmation, send_bank_transfer_notification
from app.services.notifications import notify_payment_confirmed, notify_bank_transfer_received
from app.redis import check_rate_limit
from app.schemas.payment import PaymentInitialize

router = APIRouter()


# --- Paystack ---
@router.post("/paystack/initialize")
async def paystack_initialize(
    body: PaymentInitialize,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Rate limit: 10 payment inits per minute per user
    if not await check_rate_limit(f"rl:paystack:init:{user.id}", 10, 60):
        raise HTTPException(status_code=429, detail="Too many payment requests. Please wait.")

    import httpx

    order_number = body.order_number
    result = await db.execute(select(Order).where(Order.order_number == order_number, Order.user_id == user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Prevent re-initialization of already paid orders
    if order.payment_status == PaymentStatus.success.value:
        raise HTTPException(status_code=400, detail="Order already paid")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.paystack.co/transaction/initialize",
            headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
            json={
                "email": order.email,
                "amount": order.total * 100,  # Paystack uses kobo
                "reference": f"{order.order_number}-PS",
                "callback_url": f"{settings.frontend_url}/checkout/callback?gateway=paystack",
                "metadata": {"order_number": order.order_number},
            },
        )
    data = resp.json()
    if not data.get("status"):
        raise HTTPException(status_code=400, detail=data.get("message", "Payment initialization failed"))

    order.payment_gateway = PaymentGateway.paystack.value
    order.payment_ref = f"{order.order_number}-PS"
    await db.flush()

    return {"authorization_url": data["data"]["authorization_url"], "reference": order.payment_ref}


@router.post("/paystack/webhook")
async def paystack_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    import hmac, hashlib

    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not settings.paystack_secret_key:
        raise HTTPException(status_code=400, detail="Webhook not configured")

    computed = hmac.new(settings.paystack_secret_key.encode(), body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(computed, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = await request.json()
    if event.get("event") != "charge.success":
        return {"status": "ignored"}

    ref = event["data"]["reference"]
    result = await db.execute(select(Order).where(Order.payment_ref == ref).options(selectinload(Order.items)))
    order = result.scalar_one_or_none()
    if order and order.payment_status != PaymentStatus.success.value:
        order.payment_status = PaymentStatus.success.value
        order.status = OrderStatus.in_production.value
        db.add(OrderTracking(order_id=order.id, status=OrderStatus.in_production.value, description="Payment confirmed via Paystack"))
        await db.flush()

        # In-app notification
        if order.user_id:
            try:
                await notify_payment_confirmed(db, order.user_id, order.order_number)
            except Exception:
                pass

        # Send confirmation email
        try:
            await send_order_confirmation(
                order.email, order.order_number, order.customer_name,
                order.total, [{"name": i.product_name, "qty": i.qty, "unitPrice": i.unit_price} for i in order.items]
            )
        except Exception:
            pass

    return {"status": "ok"}


# --- Flutterwave ---
@router.post("/flutterwave/initialize")
async def flutterwave_initialize(
    body: PaymentInitialize,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Rate limit: 10 payment inits per minute per user
    if not await check_rate_limit(f"rl:flutterwave:init:{user.id}", 10, 60):
        raise HTTPException(status_code=429, detail="Too many payment requests. Please wait.")

    import httpx

    order_number = body.order_number
    result = await db.execute(select(Order).where(Order.order_number == order_number, Order.user_id == user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_status == PaymentStatus.success.value:
        raise HTTPException(status_code=400, detail="Order already paid")

    tx_ref = f"{order.order_number}-FW"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.flutterwave.com/v3/payments",
            headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"},
            json={
                "tx_ref": tx_ref,
                "amount": order.total,
                "currency": "NGN",
                "redirect_url": f"{settings.frontend_url}/checkout/callback?gateway=flutterwave",
                "customer": {"email": order.email, "name": order.customer_name},
                "meta": {"order_number": order.order_number},
            },
        )
    data = resp.json()
    if data.get("status") != "success":
        raise HTTPException(status_code=400, detail=data.get("message", "Payment initialization failed"))

    order.payment_gateway = PaymentGateway.flutterwave.value
    order.payment_ref = tx_ref
    await db.flush()

    return {"authorization_url": data["data"]["link"], "reference": tx_ref}


@router.post("/flutterwave/webhook")
async def flutterwave_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    import hmac

    signature = request.headers.get("verif-hash", "")
    expected = settings.flutterwave_webhook_secret or settings.flutterwave_secret_key
    if not expected or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = await request.json()
    if event.get("event") != "charge.completed":
        return {"status": "ignored"}

    tx_ref = event["data"]["tx_ref"]
    result = await db.execute(select(Order).where(Order.payment_ref == tx_ref).options(selectinload(Order.items)))
    order = result.scalar_one_or_none()
    if order and order.payment_status != PaymentStatus.success.value:
        order.payment_status = PaymentStatus.success.value
        order.status = OrderStatus.in_production.value
        db.add(OrderTracking(order_id=order.id, status=OrderStatus.in_production.value, description="Payment confirmed via Flutterwave"))
        await db.flush()

        # In-app notification
        if order.user_id:
            try:
                await notify_payment_confirmed(db, order.user_id, order.order_number)
            except Exception:
                pass

        # Send confirmation email
        try:
            await send_order_confirmation(
                order.email, order.order_number, order.customer_name,
                order.total, [{"name": i.product_name, "qty": i.qty, "unitPrice": i.unit_price} for i in order.items]
            )
        except Exception:
            pass

    return {"status": "ok"}


# --- Payment verification (callback) ---
@router.get("/verify")
async def verify_payment(
    gateway: str,
    reference: str | None = None,
    transaction_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if gateway == "paystack" and reference:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
            )
        data = resp.json()
        if data.get("status") and data["data"]["status"] == "success":
            result = await db.execute(select(Order).where(Order.payment_ref == reference).options(selectinload(Order.items)))
            order = result.scalar_one_or_none()
            if order and order.payment_status != PaymentStatus.success.value:
                order.payment_status = PaymentStatus.success.value
                order.status = OrderStatus.in_production.value
                db.add(OrderTracking(order_id=order.id, status=OrderStatus.in_production.value, description="Payment verified"))
                await db.flush()

                if order.user_id:
                    try:
                        await notify_payment_confirmed(db, order.user_id, order.order_number)
                    except Exception:
                        pass

                try:
                    await send_order_confirmation(
                        order.email, order.order_number, order.customer_name,
                        order.total, [{"name": i.product_name, "qty": i.qty, "unitPrice": i.unit_price} for i in order.items]
                    )
                except Exception:
                    pass

            if order:
                return {"status": "success", "order_number": order.order_number}
        return {"status": "failed"}

    elif gateway == "flutterwave" and transaction_id:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
                headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"},
            )
        data = resp.json()
        if data.get("status") == "success" and data["data"]["status"] == "successful":
            tx_ref = data["data"]["tx_ref"]
            result = await db.execute(select(Order).where(Order.payment_ref == tx_ref).options(selectinload(Order.items)))
            order = result.scalar_one_or_none()
            if order and order.payment_status != PaymentStatus.success.value:
                order.payment_status = PaymentStatus.success.value
                order.status = OrderStatus.in_production.value
                db.add(OrderTracking(order_id=order.id, status=OrderStatus.in_production.value, description="Payment verified"))
                await db.flush()

                if order.user_id:
                    try:
                        await notify_payment_confirmed(db, order.user_id, order.order_number)
                    except Exception:
                        pass

                try:
                    await send_order_confirmation(
                        order.email, order.order_number, order.customer_name,
                        order.total, [{"name": i.product_name, "qty": i.qty, "unitPrice": i.unit_price} for i in order.items]
                    )
                except Exception:
                    pass

            if order:
                return {"status": "success", "order_number": order.order_number}
        return {"status": "failed"}

    raise HTTPException(status_code=400, detail="Invalid verification request")


# --- Bank Accounts ---
@router.get("/bank-accounts")
async def list_bank_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).where(BankAccount.is_active == True).order_by(BankAccount.sort_order))
    accounts = result.scalars().all()
    return [{"id": a.id, "bank_name": a.bank_name, "account_name": a.account_name, "account_number": a.account_number} for a in accounts]


# --- Bank Transfer Proof Upload ---
@router.post("/orders/{order_number}/proof-of-payment")
async def upload_proof(
    order_number: str,
    proof: UploadFile = File(...),
    amount: int = Form(...),
    bank_name: str = Form(...),
    deposit_date: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    from pathlib import Path

    result = await db.execute(select(Order).where(Order.order_number == order_number.upper(), Order.user_id == user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_status == PaymentStatus.success.value:
        raise HTTPException(status_code=400, detail="Order already paid")

    # Validate file type
    allowed_extensions = {"jpg", "jpeg", "png", "pdf"}
    ext = proof.filename.split(".")[-1].lower() if proof.filename and "." in proof.filename else "jpg"
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: JPG, PNG, PDF")

    # Save file
    filename = f"{uuid_mod.uuid4()}.{ext}"
    upload_path = Path(settings.upload_dir) / "proofs" / filename
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    content = await proof.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    with open(upload_path, "wb") as f:
        f.write(content)

    order.bank_transfer_proof_url = f"/uploads/proofs/{filename}"
    order.payment_gateway = PaymentGateway.bank_transfer.value
    order.payment_status = PaymentStatus.awaiting_verification.value
    db.add(OrderTracking(
        order_id=order.id,
        status=OrderStatus.pending_payment.value,
        description=f"Proof of payment uploaded. Amount: ₦{amount:,}, Bank: {bank_name}, Date: {deposit_date}",
    ))
    await db.flush()

    # In-app notification to customer
    if order.user_id:
        try:
            await notify_bank_transfer_received(db, order.user_id, order.order_number)
        except Exception:
            pass

    # Notify admin of new proof upload
    try:
        await send_bank_transfer_notification(order.order_number, order.customer_name)
    except Exception:
        pass

    return {"message": "Proof of payment uploaded", "order_number": order.order_number}
