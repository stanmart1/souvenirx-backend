import uuid
import random
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user, get_guest_or_user
from app.models.user import User
from app.models.guest_session import GuestSession
from app.models.order import Order, OrderItem, OrderTracking, OrderStatus, PaymentStatus
from app.models.product import Product, ProductTier, ProductImage
from app.models.cart import CartItem
from app.models.delivery import DeliveryZone
from app.models.promo import PromoCode
from app.models.affiliate import Affiliate, AffiliateConversion, AffiliateStatus
from app.services.email import send_order_confirmation
from app.services.notifications import notify_order_placed, notify_order_cancelled
from app.schemas.cart import OrderCreate

router = APIRouter()

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class OrderItemUpdate(BaseModel):
    action: str          # "add" | "remove" | "update_qty"
    product_id: str      # UUID of product
    qty: int | None = None  # required for add / update_qty


PHONE_REGEX = re.compile(r"^[0-9+\-\s()]{7,20}$")


async def _generate_unique_order_number(db: AsyncSession) -> str:
    """Generate a unique order number with retry logic."""
    for _ in range(10):
        order_number = f"SVX-{random.randint(10000, 99999)}"
        result = await db.execute(select(Order.id).where(Order.order_number == order_number))
        if not result.scalar_one_or_none():
            return order_number
    # Fallback to UUID-based if all random attempts collide
    return f"SVX-{uuid.uuid4().hex[:8].upper()}"


@router.post("")
async def create_order(
    body: OrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Support both registered users and guest sessions
    user_or_guest = await get_guest_or_user(request, db)
    user = user_or_guest[0]
    guest = user_or_guest[1]
    
    # Require email verification for registered users
    if user and not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email address before placing an order. Check your inbox for the verification link."
        )
    
    # Idempotency: when the client supplies X-Idempotency-Key, dedupe retries
    # for 1h. When absent, we don't enforce (client is responsible for retries).
    client_idempotency_key = request.headers.get("X-Idempotency-Key")
    if client_idempotency_key:
        from app.redis import check_idempotency
        if not await check_idempotency(f"idempotency:{client_idempotency_key}"):
            raise HTTPException(status_code=409, detail="Duplicate order request")

    # Validate required fields
    customer_name = body.customer_name
    email = body.email
    phone = body.phone or ""
    address = body.address or ""
    city = body.city or ""
    state = body.state or ""

    if not all([customer_name, email, phone, address, city, state]):
        raise HTTPException(status_code=400, detail="All customer fields are required")
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if not PHONE_REGEX.match(phone):
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    # Get cart items - from user cart or guest session
    cart_items = []
    if user:
        result = await db.execute(
            select(CartItem)
            .where(CartItem.user_id == user.id)
            .options(selectinload(CartItem.product).selectinload(Product.tiers))
        )
        cart_items = result.scalars().all()
    elif guest:
        # For guest, parse cart from guest session data
        import json
        if guest.cart_data:
            cart_data = json.loads(guest.cart_data)
            # Load products from cart data
            for item_data in cart_data:
                result = await db.execute(
                    select(Product)
                    .where(Product.id == uuid.UUID(item_data["productId"]))
                    .options(selectinload(Product.tiers))
                )
                product = result.scalar_one_or_none()
                if product:
                    # Create a temporary CartItem-like object
                    class TempCartItem:
                        def __init__(self, product, qty, customization):
                            self.product = product
                            self.qty = qty
                            self.customization = customization
                    cart_items.append(TempCartItem(product, item_data["qty"], item_data.get("customization", {})))
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Check stock and calculate totals
    subtotal = 0
    order_items_data = []
    for ci in cart_items:
        if ci.qty > ci.product.stock:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {ci.product.name}. Available: {ci.product.stock}"
            )

        unit_price = ci.product.base_price
        for tier in sorted(ci.product.tiers, key=lambda t: t.min_qty):
            if ci.qty >= tier.min_qty:
                unit_price = tier.unit_price
        subtotal += unit_price * ci.qty
        order_items_data.append({
            "product_id": ci.product.id,
            "product_name": ci.product.name,
            "qty": ci.qty,
            "unit_price": unit_price,
            "customization": ci.customization,
        })

    # Shipping
    zone_name = body.delivery_zone or "Lagos Mainland"
    method = body.delivery_method or "standard"
    result = await db.execute(select(DeliveryZone).where(DeliveryZone.zone_name == zone_name))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=400, detail="Invalid delivery zone")
    shipping = 0 if method == "pickup" else (zone.express_fee if method == "express" else zone.standard_fee)

    # Promo discount
    discount_amount = body.discount_amount or 0
    total = subtotal + shipping - discount_amount
    if total < 0:
        total = 0

    # Generate unique order number
    order_number = await _generate_unique_order_number(db)

    # Create order
    order = Order(
        order_number=order_number,
        user_id=user.id if user else None,
        customer_name=customer_name,
        email=email,
        phone=phone,
        address=address,
        city=city,
        state=state,
        delivery_zone=zone_name,
        delivery_method=method,
        subtotal=subtotal,
        shipping_fee=shipping,
        total=total,
        status=OrderStatus.pending_payment.value,
        payment_status=PaymentStatus.pending.value,
        promo_code=body.promo_code,
        discount_amount=discount_amount,
        event_date=body.event_date,
        estimated_delivery=zone.eta_text,
    )
    db.add(order)
    await db.flush()

    # Create order items and decrement stock atomically.
    for item_data in order_items_data:
        db.add(OrderItem(order_id=order.id, **item_data))
        result = await db.execute(
            Product.__table__.update()
            .where(Product.id == item_data["product_id"])
            .where(Product.stock >= item_data["qty"])
            .values(stock=Product.stock - item_data["qty"])
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=409,
                detail=f"Stock changed for {item_data['product_name']}. Please review your cart.",
            )

    # Add initial tracking event
    db.add(OrderTracking(
        order_id=order.id,
        status=OrderStatus.pending_payment.value,
        description="Order placed, awaiting payment",
    ))

    # Clear cart (for registered users)
    if user:
        for ci in cart_items:
            await db.delete(ci)
    elif guest:
        # Clear guest cart
        guest.cart_data = None

    # Increment promo usage
    if body.promo_code:
        promo_result = await db.execute(select(PromoCode).where(PromoCode.code == body.promo_code.upper()))
        promo = promo_result.scalar_one_or_none()
        if promo:
            promo.current_uses += 1

    # Track affiliate conversion from referral cookie
    ref_code = request.cookies.get("svx_ref")
    if ref_code:
        aff_result = await db.execute(
            select(Affiliate).where(
                Affiliate.referral_code == ref_code,
                Affiliate.status == AffiliateStatus.active.value,
            )
        )
        affiliate = aff_result.scalar_one_or_none()
        if affiliate and (not user or affiliate.user_id != user.id):
            commission = int(subtotal * affiliate.commission_rate)
            db.add(AffiliateConversion(
                affiliate_id=affiliate.id,
                order_id=order.id,
                commission_amount=commission,
                status="pending",
            ))
            affiliate.total_earnings += commission

    await db.flush()

    # In-app notification for logged-in users
    if user:
        try:
            await notify_order_placed(db, user.id, order_number)
        except Exception:
            pass

    # Send order confirmation email (non-blocking)
    try:
        items_for_email = [{"name": d["product_name"], "qty": d["qty"], "unitPrice": d["unit_price"]} for d in order_items_data]
        await send_order_confirmation(email, order_number, customer_name, total, items_for_email)
    except Exception:
        pass  # Don't fail order creation if email fails

    return {
        "order_number": order.order_number,
        "total": order.total,
        "message": "Order created successfully",
    }


@router.get("")
async def list_orders(
    status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    query = select(Order).where(Order.user_id == user.id)
    
    if status:
        query = query.where(Order.status == status)
    
    if search:
        query = query.where(
            or_(
                Order.order_number.ilike(f"%{search}%"),
                Order.customer_name.ilike(f"%{search}%"),
            )
        )

    count_result = await db.execute(
        select(func.count()).where(Order.user_id == user.id)
    )
    total = count_result.scalar()

    result = await db.execute(
        query
        .options(
            selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.images)
        )
        .order_by(Order.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    orders = result.scalars().all()

    return {
        "orders": [_order_summary(o) for o in orders],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/{order_number}")
async def get_order(
    order_number: str,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .where(Order.order_number == order_number.upper())
        .options(selectinload(Order.items), selectinload(Order.tracking))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # If user is authenticated and owns the order, return full detail
    # If user is admin, return full detail
    # Otherwise, return limited public info (no PII)
    is_admin = False
    if current_user:
        from app.services.rbac import user_has_role
        is_admin = await user_has_role(db, current_user, "admin")
    if current_user and (order.user_id == current_user.id or is_admin):
        return _order_detail(order)
    return _order_detail_public(order)


@router.get("/{order_number}/track")
async def track_order(order_number: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order)
        .where(Order.order_number == order_number.upper())
        .options(selectinload(Order.items), selectinload(Order.tracking))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_detail(order)


@router.post("/{order_number}/cancel")
async def cancel_order(
    order_number: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.order_number == order_number.upper(), Order.user_id == user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in (OrderStatus.pending_payment.value,):
        raise HTTPException(status_code=400, detail="Order cannot be cancelled at this stage")

    order.status = OrderStatus.cancelled.value
    order.payment_status = PaymentStatus.failed.value
    db.add(OrderTracking(order_id=order.id, status=OrderStatus.cancelled.value, description="Order cancelled by customer"))
    await notify_order_cancelled(db, user.id, order.order_number)
    await db.flush()
    return {"message": "Order cancelled"}


@router.patch("/{order_number}/items")
async def modify_order_items(
    order_number: str,
    body: OrderItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Modify items on a pending order (add / remove / update_qty)."""
    result = await db.execute(
        select(Order)
        .where(Order.order_number == order_number.upper(), Order.user_id == user.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.pending_payment.value:
        raise HTTPException(
            status_code=400,
            detail="Order can only be modified while in pending_payment status",
        )

    try:
        product_uuid = uuid.UUID(body.product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product_id format")

    action = body.action

    if action == "remove":
        if len(order.items) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last item")
        item = next((i for i in order.items if i.product_id == product_uuid), None)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found in order")
        await db.delete(item)

    elif action in ("update_qty", "add"):
        if body.qty is None:
            raise HTTPException(status_code=400, detail="qty is required for this action")

        # Fetch product with tiers to validate MOQ and price
        prod_result = await db.execute(
            select(Product)
            .where(Product.id == product_uuid)
            .options(selectinload(Product.tiers))
        )
        product = prod_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if body.qty < product.moq:
            raise HTTPException(
                status_code=400,
                detail=f"Quantity must be at least {product.moq} (MOQ)",
            )

        # Resolve tiered unit price
        unit_price = product.base_price
        for tier in sorted(product.tiers, key=lambda t: t.min_qty):
            if body.qty >= tier.min_qty:
                unit_price = tier.unit_price

        existing_item = next((i for i in order.items if i.product_id == product_uuid), None)

        if action == "update_qty":
            if not existing_item:
                raise HTTPException(status_code=404, detail="Item not found in order")
            existing_item.qty = body.qty
            existing_item.unit_price = unit_price
        else:  # add
            if existing_item:
                # Item already exists — treat as update_qty
                existing_item.qty = body.qty
                existing_item.unit_price = unit_price
            else:
                db.add(OrderItem(
                    order_id=order.id,
                    product_id=product_uuid,
                    product_name=product.name,
                    qty=body.qty,
                    unit_price=unit_price,
                ))
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid action. Use 'add', 'remove', or 'update_qty'",
        )

    await db.flush()

    # Recalculate order total from all current items
    items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    all_items = items_result.scalars().all()
    order.total = sum(i.unit_price * i.qty for i in all_items)

    # Record tracking entry
    db.add(OrderTracking(
        order_id=order.id,
        status=order.status,
        description=f"Order modified by customer: {action} {body.product_id}",
    ))

    await db.flush()
    return {"order_number": order.order_number, "total": order.total, "message": "Order updated"}


@router.post("/{order_number}/reorder")
async def reorder_items(
    order_number: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Copy items from a previous order to the current user's cart."""
    result = await db.execute(
        select(Order)
        .where(Order.order_number == order_number.upper(), Order.user_id == user.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Check stock and validate products
    unavailable_items = []
    available_items = []
    
    for order_item in order.items:
        result = await db.execute(
            select(Product)
            .where(Product.id == order_item.product_id)
            .options(selectinload(Product.tiers))
        )
        product = result.scalar_one_or_none()
        
        if not product or not product.is_active:
            unavailable_items.append({
                "product_name": order_item.product_name,
                "reason": "Product no longer available"
            })
        elif product.stock < order_item.qty:
            unavailable_items.append({
                "product_name": order_item.product_name,
                "reason": f"Insufficient stock (available: {product.stock})"
            })
        else:
            # Calculate current price
            unit_price = product.base_price
            for tier in sorted(product.tiers, key=lambda t: t.min_qty):
                if order_item.qty >= tier.min_qty:
                    unit_price = tier.unit_price
            
            available_items.append({
                "product_id": str(product.id),
                "product_name": product.name,
                "qty": order_item.qty,
                "unit_price": unit_price,
                "customization": order_item.customization or {},
            })
    
    # Clear existing cart and add available items
    from app.models.cart import CartItem
    
    # Delete existing cart items
    existing_cart = await db.execute(
        select(CartItem).where(CartItem.user_id == user.id)
    )
    for existing in existing_cart.scalars().all():
        await db.delete(existing)
    
    # Add available items to cart
    for item in available_items:
        cart_item = CartItem(
            user_id=user.id,
            product_id=uuid.UUID(item["product_id"]),
            qty=item["qty"],
            customization=item["customization"],
        )
        db.add(cart_item)
    
    await db.flush()
    
    return {
        "message": f"Added {len(available_items)} items to cart",
        "added_count": len(available_items),
        "unavailable_count": len(unavailable_items),
        "unavailable_items": unavailable_items,
    }


def _order_summary(o: Order) -> dict:
    images = []
    for item in o.items:
        if item.product and item.product.images:
            for img in item.product.images:
                if img.url not in images:
                    images.append(img.url)
        if item.design_preview_url and item.design_preview_url not in images:
            images.append(item.design_preview_url)
    return {
        "id": o.order_number,
        "customer": o.customer_name,
        "items": len(o.items),
        "total": o.total,
        "status": o.status,
        "date": o.created_at.strftime("%Y-%m-%d"),
        "payment_status": o.payment_status,
        "estimatedDelivery": o.estimated_delivery,
        "images": images[:5],
    }


def _order_detail(o: Order) -> dict:
    return {
        "id": o.order_number,
        "customer": o.customer_name,
        "email": o.email,
        "phone": o.phone,
        "address": f"{o.address}, {o.city}, {o.state}",
        "items": [{"name": i.product_name, "qty": i.qty, "unitPrice": i.unit_price} for i in o.items],
        "subtotal": o.subtotal,
        "shipping": o.shipping_fee,
        "total": o.total,
        "status": o.status,
        "payment_status": o.payment_status,
        "payment_gateway": o.payment_gateway,
        "bank_transfer_proof_url": o.bank_transfer_proof_url,
        "date": o.created_at.strftime("%Y-%m-%d"),
        "deliveryZone": o.delivery_zone,
        "deliveryMethod": o.delivery_method,
        "estimatedDelivery": o.estimated_delivery,
        "timeline": [
            {
                "status": t.status,
                "date": t.created_at.strftime("%Y-%m-%d"),
                "time": t.created_at.strftime("%I:%M %p"),
                "description": t.description,
            }
            for t in o.tracking
        ],
    }


def _order_detail_public(o: Order) -> dict:
    """Public order detail without sensitive PII."""
    return {
        "id": o.order_number,
        "customer": o.customer_name,
        "items": [{"name": i.product_name, "qty": i.qty, "unitPrice": i.unit_price} for i in o.items],
        "subtotal": o.subtotal,
        "shipping": o.shipping_fee,
        "total": o.total,
        "status": o.status,
        "payment_status": o.payment_status,
        "bank_transfer_proof_url": o.bank_transfer_proof_url,
        "date": o.created_at.strftime("%Y-%m-%d"),
        "deliveryZone": o.delivery_zone,
        "deliveryMethod": o.delivery_method,
        "estimatedDelivery": o.estimated_delivery,
        "timeline": [
            {
                "status": t.status,
                "date": t.created_at.strftime("%Y-%m-%d"),
                "time": t.created_at.strftime("%I:%M %p"),
                "description": t.description,
            }
            for t in o.tracking
        ],
    }
