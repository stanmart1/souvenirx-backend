import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.user import User, UserRole
from app.models.product import Product, Category, ProductImage, ProductTier, ProductCustomization, ProductVariant, ProductGroup
from app.models.order import Order, OrderTracking, OrderStatus, PaymentStatus, OrderItem
from app.models.review import Review
from app.models.affiliate import Affiliate, AffiliatePayout, PayoutStatus, AffiliateStatus, AffiliateClick, AffiliateConversion
from app.models.delivery import DeliveryZone
from app.models.promo import PromoCode
from app.models.bank_account import BankAccount
from app.models.settings import Settings, HomepageContent, Ad, EmailTemplate
from app.models.logo_upload import LogoUpload, LogoUploadStatus
from app.models.cart import CartItem
from app.services.notifications import (
    notify_order_status_changed,
    notify_payment_confirmed,
    notify_payment_rejected,
    notify_affiliate_approved,
    notify_affiliate_suspended,
    notify_payout_processed,
)
from app.schemas.ad import AdCreate, AdUpdate
from app.schemas.email_template import EmailTemplateCreate, EmailTemplateUpdate
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.payment import (
    OrderStatusUpdate,
    BankTransferVerify,
    AffiliatePayoutRequest,
    AffiliateUpdate,
    DeliveryZoneUpdate,
    BankAccountCreate,
    BankAccountUpdate,
    PromoCreate,
    PromoUpdate,
)

router = APIRouter()


# --- Dashboard ---
@router.get("/stats")
async def dashboard_stats(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from datetime import timedelta
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)

    # Revenue (30 days)
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total), 0))
        .where(Order.payment_status == PaymentStatus.success, Order.created_at >= thirty_days_ago)
    )
    revenue = revenue_result.scalar()

    # Revenue (previous 30 days for trend)
    revenue_prev_result = await db.execute(
        select(func.coalesce(func.sum(Order.total), 0))
        .where(Order.payment_status == PaymentStatus.success, Order.created_at >= sixty_days_ago, Order.created_at < thirty_days_ago)
    )
    revenue_prev = revenue_prev_result.scalar()

    # Calculate revenue trend
    revenue_trend = 0
    if revenue_prev > 0:
        revenue_trend = round(((revenue - revenue_prev) / revenue_prev) * 100, 1)

    # Orders count (30 days)
    orders_result = await db.execute(
        select(func.count()).where(Order.created_at >= thirty_days_ago)
    )
    total_orders = orders_result.scalar()

    # Orders count (previous 30 days for trend)
    orders_prev_result = await db.execute(
        select(func.count()).where(Order.created_at >= sixty_days_ago, Order.created_at < thirty_days_ago)
    )
    total_orders_prev = orders_prev_result.scalar()

    # Calculate orders trend
    orders_trend = 0
    if total_orders_prev > 0:
        orders_trend = round(((total_orders - total_orders_prev) / total_orders_prev) * 100, 1)

    # Customers count (all time)
    customers_result = await db.execute(select(func.count()).where(User.role == UserRole.customer.value))
    total_customers = customers_result.scalar()

    # Customers count (previous 30 days for trend)
    customers_prev_result = await db.execute(
        select(func.count()).where(User.role == UserRole.customer.value, User.created_at >= sixty_days_ago, User.created_at < thirty_days_ago)
    )
    total_customers_prev = customers_prev_result.scalar()

    # Calculate customers trend
    customers_trend = 0
    if total_customers_prev > 0:
        customers_trend = round(((total_customers - total_customers_prev) / total_customers_prev) * 100, 1)

    # Avg order value (30 days)
    avg_result = await db.execute(
        select(func.coalesce(func.avg(Order.total), 0))
        .where(Order.payment_status == PaymentStatus.success, Order.created_at >= thirty_days_ago)
    )
    avg_order = avg_result.scalar()

    # Avg order value (previous 30 days for trend)
    avg_prev_result = await db.execute(
        select(func.coalesce(func.avg(Order.total), 0))
        .where(Order.payment_status == PaymentStatus.success, Order.created_at >= sixty_days_ago, Order.created_at < thirty_days_ago)
    )
    avg_order_prev = avg_prev_result.scalar()

    # Calculate avg order trend
    avg_order_trend = 0
    if avg_order_prev > 0:
        avg_order_trend = round(((avg_order - avg_order_prev) / avg_order_prev) * 100, 1)

    return {
        "revenue": revenue,
        "revenue_trend": revenue_trend,
        "orders": total_orders,
        "orders_trend": orders_trend,
        "customers": total_customers,
        "customers_trend": customers_trend,
        "avg_order_value": int(avg_order),
        "avg_order_trend": avg_order_trend,
    }


@router.get("/analytics/sales")
async def sales_analytics(
    period: str = "30d",  # 7d, 30d, 90d, 1y
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta

    # Determine date range
    period_map = {
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
    }
    days_delta = period_map.get(period, timedelta(days=30))
    start_date = datetime.now(timezone.utc) - days_delta

    # Daily revenue data
    daily_revenue_result = await db.execute(
        select(
            func.date(Order.created_at).label('date'),
            func.sum(Order.total).label('revenue'),
            func.count(Order.id).label('orders'),
        )
        .where(Order.payment_status == PaymentStatus.success, Order.created_at >= start_date)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )
    daily_data = daily_revenue_result.all()

    # Top products
    top_products_result = await db.execute(
        select(OrderItem.product_name, func.sum(OrderItem.qty).label('total_sold'), func.sum(OrderItem.qty * OrderItem.unit_price).label('revenue'))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.payment_status == PaymentStatus.success, Order.created_at >= start_date)
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.qty * OrderItem.unit_price).desc())
        .limit(10)
    )
    top_products = top_products_result.all()

    return {
        "daily_data": [
            {
                "date": str(d.date),
                "revenue": d.revenue or 0,
                "orders": d.orders or 0,
            }
            for d in daily_data
        ],
        "top_products": [
            {
                "name": p.product_name,
                "total_sold": p.total_sold or 0,
                "revenue": p.revenue or 0,
            }
            for p in top_products
        ],
    }


@router.get("/analytics/products")
async def product_analytics(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # Product performance
    product_performance_result = await db.execute(
        select(
            Product.id,
            Product.name,
            Product.slug,
            Product.base_price,
            Product.stock,
            func.coalesce(func.sum(OrderItem.qty), 0).label('total_sold'),
            func.coalesce(func.sum(OrderItem.qty * OrderItem.unit_price), 0).label('revenue'),
            func.count(Order.id).label('order_count'),
        )
        .outerjoin(OrderItem, Product.id == OrderItem.product_id)
        .outerjoin(Order, OrderItem.order_id == Order.id)
        .where(Order.created_at >= thirty_days_ago)
        .group_by(Product.id, Product.name, Product.slug, Product.base_price, Product.stock)
        .order_by(func.coalesce(func.sum(OrderItem.qty * OrderItem.unit_price), 0).desc())
        .limit(20)
    )
    products = product_performance_result.all()

    # Low stock alert
    low_stock_result = await db.execute(
        select(Product.name, Product.stock)
        .where(Product.stock < 10, Product.is_active == True)
        .order_by(Product.stock.asc())
        .limit(10)
    )
    low_stock = low_stock_result.all()

    return {
        "top_products": [
            {
                "id": str(p.id),
                "name": p.name,
                "slug": p.slug,
                "base_price": p.base_price,
                "stock": p.stock,
                "total_sold": p.total_sold or 0,
                "revenue": p.revenue or 0,
                "order_count": p.order_count or 0,
            }
            for p in products
        ],
        "low_stock": [
            {
                "name": p.name,
                "stock": p.stock,
            }
            for p in low_stock
        ],
    }


@router.get("/analytics/customers")
async def customer_analytics(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta

    # Customer acquisition (new customers per month)
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
    acquisition_result = await db.execute(
        select(
            func.date_trunc('month', User.created_at).label('month'),
            func.count(User.id).label('new_customers'),
        )
        .where(User.role == UserRole.customer.value, User.created_at >= six_months_ago)
        .group_by(func.date_trunc('month', User.created_at))
        .order_by(func.date_trunc('month', User.created_at))
    )
    acquisition_data = acquisition_result.all()

    # Top customers by spend
    top_customers_result = await db.execute(
        select(
            User.id,
            User.full_name,
            User.email,
            func.coalesce(func.sum(Order.total), 0).label('total_spent'),
            func.count(Order.id).label('order_count'),
        )
        .join(Order, User.id == Order.user_id)
        .where(User.role == UserRole.customer.value, Order.payment_status == PaymentStatus.success.value)
        .group_by(User.id, User.full_name, User.email)
        .order_by(func.coalesce(func.sum(Order.total), 0).desc())
        .limit(10)
    )
    top_customers = top_customers_result.all()

    return {
        "acquisition": [
            {
                "month": str(a.month),
                "new_customers": a.new_customers,
            }
            for a in acquisition_data
        ],
        "top_customers": [
            {
                "id": str(c.id),
                "name": c.full_name,
                "email": c.email,
                "total_spent": c.total_spent or 0,
                "order_count": c.order_count or 0,
            }
            for c in top_customers
        ],
    }


@router.get("/analytics/inventory")
async def inventory_analytics(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    # Inventory status
    total_products_result = await db.execute(
        select(func.count()).where(Product.is_active == True)
    )
    total_products = total_products_result.scalar()

    low_stock_result = await db.execute(
        select(func.count()).where(Product.stock < 10, Product.is_active == True)
    )
    low_stock_count = low_stock_result.scalar()

    out_of_stock_result = await db.execute(
        select(func.count()).where(Product.stock == 0, Product.is_active == True)
    )
    out_of_stock_count = out_of_stock_result.scalar()

    # Category breakdown
    category_breakdown_result = await db.execute(
        select(
            Category.name,
            func.count(Product.id).label('product_count'),
            func.sum(Product.stock).label('total_stock'),
        )
        .join(Product, Category.id == Product.category_id)
        .where(Product.is_active == True)
        .group_by(Category.name)
        .order_by(func.count(Product.id).desc())
    )
    category_breakdown = category_breakdown_result.all()

    return {
        "summary": {
            "total_products": total_products or 0,
            "low_stock": low_stock_count or 0,
            "out_of_stock": out_of_stock_count or 0,
        },
        "category_breakdown": [
            {
                "category": c.name,
                "product_count": c.product_count or 0,
                "total_stock": c.total_stock or 0,
            }
            for c in category_breakdown
        ],
    }


# --- Categories CRUD ---
@router.get("/categories")
async def list_categories(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    categories = result.scalars().all()
    return [
        {
            "id": c.id, "slug": c.slug, "name": c.name,
            "icon": c.icon, "sort_order": c.sort_order,
            "product_count": len(c.products) if c.products else 0
        }
        for c in categories
    ]


@router.post("/categories")
async def create_category(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    category = Category(
        slug=body["slug"],
        name=body["name"],
        icon=body.get("icon", "📦"),
        sort_order=body.get("sort_order", 0),
    )
    db.add(category)
    await db.flush()
    return {"id": category.id, "message": "Category created"}


@router.put("/categories/{category_id}")
async def update_category(
    category_id: int,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if "name" in body:
        category.name = body["name"]
    if "icon" in body:
        category.icon = body["icon"]
    if "sort_order" in body:
        category.sort_order = body["sort_order"]

    await db.flush()
    return {"message": "Category updated"}


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if category has products
    if category.products:
        raise HTTPException(status_code=400, detail="Cannot delete category with products")

    await db.delete(category)
    await db.flush()
    return {"message": "Category deleted"}


# --- Products CRUD ---
@router.get("/products")
async def list_products(
    search: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).options(
        selectinload(Product.images), 
        selectinload(Product.tiers), 
        selectinload(Product.customizations), 
        selectinload(Product.category),
        selectinload(Product.variants),
        selectinload(Product.grouped_products)
    )
    if search:
        query = query.where(or_(Product.name.ilike(f"%{search}%"), Product.description.ilike(f"%{search}%")))
    if category:
        query = query.join(Category).where(Category.slug == category)

    query = query.order_by(Product.created_at.desc())
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    products = result.scalars().all()

    return [
        {
            "id": str(p.id), "slug": p.slug, "name": p.name,
            "category": p.category.slug if p.category else None,
            "basePrice": p.base_price, "moq": p.moq, "stock": p.stock,
            "images": [img.url for img in p.images],
            "tags": p.tags or [],
            "hasVariants": p.has_variants,
            "isGroupParent": p.is_group_parent,
            "tiers": [{"qty": t.min_qty, "price": t.unit_price} for t in p.tiers],
            "customizations": [
                {
                    "type": c.type,
                    "label": c.label,
                    "max_length": c.max_length,
                    "values": c.values,
                }
                for c in p.customizations
            ],
            "variants": [
                {
                    "id": str(v.id),
                    "sku": v.sku,
                    "attributes": v.attributes,
                    "price": v.price,
                    "moq": v.moq,
                    "stock": v.stock,
                }
                for v in p.variants
            ] if p.variants else [],
            "groupedProducts": [
                {
                    "id": str(gp.id),
                    "name": gp.name,
                    "basePrice": gp.base_price,
                }
                for gp in p.grouped_products
            ] if p.grouped_products else [],
        }
        for p in products
    ]


@router.post("/products")
async def create_product(body: ProductCreate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    cat_result = await db.execute(select(Category).where(Category.slug == body.category))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=400, detail="Invalid category")

    # Handle product group if this is a grouped product
    product_group_id = None
    if body.is_group_parent:
        # Create a new product group
        product_group = ProductGroup(name=f"{body.name} Bundle")
        db.add(product_group)
        await db.flush()
        product_group_id = product_group.id
    elif body.product_group_id:
        product_group_id = body.product_group_id

    product = Product(
        slug=body.slug,
        name=body.name,
        category_id=category.id,
        description=body.description,
        base_price=body.base_price,
        moq=body.moq,
        stock=body.stock,
        tags=body.tags,
        has_variants=len(body.variants) > 0,
        is_group_parent=body.is_group_parent,
        product_group_id=product_group_id,
    )
    db.add(product)
    await db.flush()

    for i, url in enumerate(body.images):
        db.add(ProductImage(product_id=product.id, url=url, alt_text=body.name, sort_order=i))
    for tier in body.tiers:
        db.add(ProductTier(product_id=product.id, min_qty=tier.min_qty, unit_price=tier.unit_price))
    for cust in body.customizations:
        db.add(ProductCustomization(
            product_id=product.id, type=cust.type, label=cust.label,
            max_length=cust.max_length, values=cust.values,
        ))
    for variant in body.variants:
        db.add(ProductVariant(
            product_id=product.id,
            sku=variant.sku,
            attributes=variant.attributes,
            price=variant.price,
            moq=variant.moq,
            stock=variant.stock,
        ))

    await db.flush()
    return {"id": str(product.id), "message": "Product created"}


@router.put("/products/{product_id}")
async def update_product(product_id: str, body: ProductUpdate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == uuid.UUID(product_id)))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field in ["name", "description", "base_price", "moq", "stock", "tags", "is_active", "is_group_parent", "product_group_id"]:
        value = getattr(body, field)
        if value is not None:
            setattr(product, field, value)
    if body.category is not None:
        cat_result = await db.execute(select(Category).where(Category.slug == body.category))
        category = cat_result.scalar_one_or_none()
        if category:
            product.category_id = category.id
    
    # Update variants if provided
    if body.variants is not None:
        # Delete existing variants
        await db.execute(select(ProductVariant).where(ProductVariant.product_id == product.id))
        # Add new variants
        for variant in body.variants:
            db.add(ProductVariant(
                product_id=product.id,
                sku=variant.sku,
                attributes=variant.attributes,
                price=variant.price,
                moq=variant.moq,
                stock=variant.stock,
            ))
        product.has_variants = len(body.variants) > 0

    await db.flush()
    
    # Invalidate product caches
    from app.redis import get_redis
    redis = await get_redis()
    if redis:
        await redis.delete("products:featured")
        await redis.delete(f"product:{product.slug}")
    
    return {"message": "Product updated"}


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == uuid.UUID(product_id)))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    await db.flush()
    return {"message": "Product deactivated"}


@router.post("/products/bulk-delete")
async def bulk_delete_products(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    product_ids = body.get("product_ids", [])
    if not product_ids:
        raise HTTPException(status_code=400, detail="No product IDs provided")

    result = await db.execute(
        select(Product).where(Product.id.in_([uuid.UUID(pid) for pid in product_ids]))
    )
    products = result.scalars().all()

    for product in products:
        product.is_active = False

    await db.flush()
    return {"message": f"Deactivated {len(products)} products"}


@router.post("/products/bulk-update-price")
async def bulk_update_price(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    product_ids = body.get("product_ids", [])
    price_change_type = body.get("type")  # "absolute" or "percentage"
    value = body.get("value", 0)

    if not product_ids:
        raise HTTPException(status_code=400, detail="No product IDs provided")
    if price_change_type not in ["absolute", "percentage"]:
        raise HTTPException(status_code=400, detail="Invalid price change type")

    result = await db.execute(
        select(Product).where(Product.id.in_([uuid.UUID(pid) for pid in product_ids]))
    )
    products = result.scalars().all()

    for product in products:
        if price_change_type == "absolute":
            product.base_price = max(0, product.base_price + value)
        else:  # percentage
            product.base_price = max(0, int(product.base_price * (1 + value / 100)))

    await db.flush()
    return {"message": f"Updated prices for {len(products)} products"}


@router.post("/products/bulk-update-stock")
async def bulk_update_stock(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    product_ids = body.get("product_ids", [])
    stock_change_type = body.get("type")  # "set" or "add"
    value = body.get("value", 0)

    if not product_ids:
        raise HTTPException(status_code=400, detail="No product IDs provided")
    if stock_change_type not in ["set", "add"]:
        raise HTTPException(status_code=400, detail="Invalid stock change type")

    result = await db.execute(
        select(Product).where(Product.id.in_([uuid.UUID(pid) for pid in product_ids]))
    )
    products = result.scalars().all()

    for product in products:
        if stock_change_type == "set":
            product.stock = max(0, value)
        else:  # add
            product.stock = max(0, product.stock + value)

    await db.flush()
    return {"message": f"Updated stock for {len(products)} products"}


# --- Orders ---
@router.get("/orders")
async def list_orders(
    status: str | None = None,
    search: str | None = None,
    payment_status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).options(selectinload(Order.items))
    if status:
        query = query.where(Order.status == status)
    if payment_status:
        query = query.where(Order.payment_status == payment_status)
    if search:
        query = query.where(or_(Order.customer_name.ilike(f"%{search}%"), Order.order_number.ilike(f"%{search}%")))
    if date_from:
        from datetime import datetime
        query = query.where(Order.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        from datetime import datetime
        query = query.where(Order.created_at <= datetime.fromisoformat(date_to))

    query = query.order_by(Order.created_at.desc())
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    orders = result.scalars().all()

    return [
        {
            "id": o.order_number, "customer": o.customer_name, "items": len(o.items),
            "total": o.total, "status": o.status, "date": o.created_at.strftime("%Y-%m-%d"),
            "payment_status": o.payment_status,
            "payment_gateway": o.payment_gateway,
            "bank_transfer_proof_url": o.bank_transfer_proof_url,
        }
        for o in orders
    ]


@router.get("/orders/export")
async def export_orders(
    status: str | None = None,
    payment_status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response
    import csv
    from io import StringIO

    query = select(Order).options(selectinload(Order.items))
    if status:
        query = query.where(Order.status == status)
    if payment_status:
        query = query.where(Order.payment_status == payment_status)
    if date_from:
        from datetime import datetime
        query = query.where(Order.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        from datetime import datetime
        query = query.where(Order.created_at <= datetime.fromisoformat(date_to))

    query = query.order_by(Order.created_at.desc())
    result = await db.execute(query)
    orders = result.scalars().all()

    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Order Number", "Customer", "Email", "Phone", "Total", "Status",
        "Payment Status", "Payment Gateway", "Date", "Items Count"
    ])

    for order in orders:
        writer.writerow([
            order.order_number,
            order.customer_name,
            order.email,
            order.phone,
            order.total,
            order.status,
            order.payment_status,
            order.payment_gateway or "N/A",
            order.created_at.strftime("%Y-%m-%d %H:%M"),
            len(order.items),
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders_export.csv"}
    )


@router.patch("/orders/{order_number}/status")
async def update_order_status(
    order_number: str,
    body: OrderStatusUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services.email import send_order_status_update

    result = await db.execute(select(Order).where(Order.order_number == order_number.upper()))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    new_status = body.status
    if new_status:
        order.status = new_status
    description = body.description or f"Status updated to {new_status}"
    db.add(OrderTracking(order_id=order.id, status=order.status, description=description))
    await db.flush()

    # In-app notification
    if order.user_id and new_status:
        try:
            await notify_order_status_changed(db, order.user_id, order.order_number, new_status)
        except Exception:
            pass

    # Send status update email
    try:
        await send_order_status_update(order.email, order.order_number, order.customer_name, new_status)
    except Exception:
        pass

    return {"message": "Order status updated"}


@router.patch("/orders/{order_number}/verify-transfer")
async def verify_bank_transfer(
    order_number: str,
    body: BankTransferVerify,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.order_number == order_number.upper()))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    from app.services.email import send_order_status_update

    if body.approved:
        order.payment_status = PaymentStatus.success.value
        order.status = OrderStatus.in_production.value
        db.add(OrderTracking(order_id=order.id, status=OrderStatus.in_production.value, description="Bank transfer verified by admin"))
        await db.flush()

        # In-app notification
        if order.user_id:
            try:
                await notify_payment_confirmed(db, order.user_id, order.order_number)
            except Exception:
                pass

        # Notify customer of approval
        try:
            await send_order_status_update(order.email, order.order_number, order.customer_name, "in_production")
        except Exception:
            pass
    else:
        order.payment_status = PaymentStatus.failed.value
        db.add(OrderTracking(order_id=order.id, status=order.status, description="Bank transfer rejected by admin"))
        await db.flush()

        # In-app notification
        if order.user_id:
            try:
                await notify_payment_rejected(db, order.user_id, order.order_number)
            except Exception:
                pass

        # Notify customer of rejection
        try:
            await send_order_status_update(order.email, order.order_number, order.customer_name, "payment_rejected")
        except Exception:
            pass

    return {"message": "Transfer verification updated"}


@router.post("/orders/{order_number}/refund")
async def process_refund(
    order_number: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.order_number == order_number.upper()))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_status != PaymentStatus.success.value:
        raise HTTPException(status_code=400, detail="Can only refund paid orders")

    refund_amount = body.get("amount", order.total)
    refund_reason = body.get("reason", "No reason provided")

    if refund_amount > order.total:
        raise HTTPException(status_code=400, detail="Refund amount cannot exceed order total")

    # Create refund record (you'd need a Refund model for full implementation)
    # For now, we'll add a tracking event
    db.add(OrderTracking(
        order_id=order.id,
        status=order.status,
        description=f"Refund processed: ₦{refund_amount:,}. Reason: {refund_reason}"
    ))

    # In a real implementation, you'd integrate with payment gateways
    # to process the actual refund

    await db.flush()
    return {"message": f"Refund of ₦{refund_amount:,} processed for order {order_number}"}


@router.post("/orders/{order_number}/return")
async def process_return(
    order_number: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.order_number == order_number.upper()))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in [OrderStatus.delivered.value]:
        raise HTTPException(status_code=400, detail="Can only process returns for delivered orders")

    return_reason = body.get("reason", "No reason provided")
    return_status = body.get("status", "pending")  # pending, approved, rejected

    # Create return tracking event
    db.add(OrderTracking(
        order_id=order.id,
        status=order.status,
        description=f"Return request: {return_status}. Reason: {return_reason}"
    ))

    await db.flush()
    return {"message": f"Return request processed for order {order_number}"}


# --- Customers ---
@router.get("/customers")
async def list_customers(
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(User).where(User.role == UserRole.customer.value)
    if search:
        query = query.where(or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    query = query.order_by(User.created_at.desc())

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    customers = result.scalars().all()

    return [
        {
            "id": str(c.id), "name": c.full_name, "email": c.email,
            "phone": c.phone, "joined": c.created_at.strftime("%Y-%m-%d"),
            "is_active": c.is_active,
        }
        for c in customers
    ]


@router.get("/customers/{customer_id}")
async def get_customer_detail(
    customer_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(customer_id), User.role == UserRole.customer.value)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get customer order statistics
    orders_result = await db.execute(
        select(func.count(), func.sum(Order.total))
        .where(Order.user_id == customer.id, Order.payment_status == PaymentStatus.success.value)
    )
    order_stats = orders_result.one()
    total_orders = order_stats[0] or 0
    total_spent = order_stats[1] or 0

    # Get recent orders
    recent_orders_result = await db.execute(
        select(Order)
        .where(Order.user_id == customer.id)
        .order_by(Order.created_at.desc())
        .limit(5)
    )
    recent_orders = recent_orders_result.scalars().all()

    return {
        "id": str(customer.id),
        "name": customer.full_name,
        "email": customer.email,
        "phone": customer.phone,
        "joined": customer.created_at.strftime("%Y-%m-%d"),
        "is_active": customer.is_active,
        "total_orders": total_orders,
        "total_spent": total_spent,
        "avg_order_value": int(total_spent / total_orders) if total_orders > 0 else 0,
        "recent_orders": [
            {
                "order_number": o.order_number,
                "total": o.total,
                "status": o.status,
                "date": o.created_at.strftime("%Y-%m-%d"),
            }
            for o in recent_orders
        ],
    }


# --- Affiliates ---
@router.get("/affiliates")
async def list_affiliates(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Affiliate).options(selectinload(Affiliate.user)))
    affiliates = result.scalars().all()
    return [
        {
            "id": str(a.id), "name": a.user.full_name, "email": a.user.email,
            "referral_code": a.referral_code, "status": a.status,
            "commission_rate": a.commission_rate, "total_earnings": a.total_earnings,
        }
        for a in affiliates
    ]


@router.get("/affiliates/{affiliate_id}/analytics")
async def get_affiliate_analytics(
    affiliate_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func
    from datetime import datetime, timedelta

    result = await db.execute(
        select(Affiliate).where(Affiliate.id == uuid.UUID(affiliate_id))
    )
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    # Get click statistics
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    clicks_result = await db.execute(
        select(func.count())
        .where(AffiliateClick.affiliate_id == affiliate.id, AffiliateClick.created_at >= thirty_days_ago)
    )
    recent_clicks = clicks_result.scalar()

    total_clicks_result = await db.execute(
        select(func.count()).where(AffiliateClick.affiliate_id == affiliate.id)
    )
    total_clicks = total_clicks_result.scalar()

    # Get conversion statistics
    conversions_result = await db.execute(
        select(func.count(), func.sum(AffiliateConversion.commission_amount))
        .where(AffiliateConversion.affiliate_id == affiliate.id)
    )
    conversion_stats = conversions_result.one()
    total_conversions = conversion_stats[0] or 0
    total_commission = conversion_stats[1] or 0

    # Get recent conversions
    recent_conversions_result = await db.execute(
        select(AffiliateConversion)
        .where(AffiliateConversion.affiliate_id == affiliate.id)
        .order_by(AffiliateConversion.created_at.desc())
        .limit(10)
    )
    recent_conversions = recent_conversions_result.scalars().all()

    # Calculate conversion rate
    conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

    return {
        "id": str(affiliate.id),
        "referral_code": affiliate.referral_code,
        "status": affiliate.status,
        "commission_rate": affiliate.commission_rate,
        "total_earnings": affiliate.total_earnings,
        "analytics": {
            "total_clicks": total_clicks,
            "recent_clicks_30d": recent_clicks,
            "total_conversions": total_conversions,
            "conversion_rate": round(conversion_rate, 2),
            "total_commission": total_commission,
        },
        "recent_conversions": [
            {
                "date": c.created_at.strftime("%Y-%m-%d"),
                "order_id": str(c.order_id),
                "commission": c.commission_amount,
                "status": c.status,
            }
            for c in recent_conversions
        ],
    }


@router.patch("/affiliates/{affiliate_id}")
async def update_affiliate(
    affiliate_id: str,
    body: AffiliateUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Affiliate).where(Affiliate.id == uuid.UUID(affiliate_id)))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    old_status = affiliate.status
    if body.status is not None:
        affiliate.status = body.status
    if body.commission_rate is not None:
        affiliate.commission_rate = body.commission_rate

    await db.flush()

    # In-app notification for status transitions
    if body.status and body.status != old_status:
        try:
            if body.status == AffiliateStatus.active.value:
                await notify_affiliate_approved(db, affiliate.user_id)
            elif body.status == AffiliateStatus.suspended.value:
                await notify_affiliate_suspended(db, affiliate.user_id)
        except Exception:
            pass

    return {"message": "Affiliate updated"}


@router.post("/affiliates/{affiliate_id}/payout")
async def process_payout(
    affiliate_id: str,
    body: AffiliatePayoutRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Affiliate).where(Affiliate.id == uuid.UUID(affiliate_id)))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    amount = body.amount if body.amount is not None else affiliate.total_earnings
    if amount <= 0 or amount > affiliate.total_earnings:
        raise HTTPException(status_code=400, detail="Invalid payout amount")

    payout = AffiliatePayout(
        affiliate_id=affiliate.id,
        amount=amount,
        status=PayoutStatus.completed.value,
        processed_at=datetime.now(timezone.utc),
    )
    db.add(payout)
    affiliate.total_earnings -= amount
    await db.flush()
    
    # In-app notification
    try:
        await notify_payout_processed(db, affiliate.user_id, amount)
    except Exception:
        pass

    # Send payout notification email
    from app.services.email import send_payout_notification_email
    user_result = await db.execute(select(User).where(User.id == affiliate.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        try:
            await send_payout_notification_email(user.email, user.full_name or "Affiliate", amount, db)
        except Exception:
            pass

    return {"message": "Payout processed", "amount": amount}


# --- Delivery Zones ---
@router.get("/delivery-zones")
async def list_zones(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeliveryZone))
    zones = result.scalars().all()
    return [
        {
            "id": z.id, 
            "zone_name": z.zone_name,
            "countries": z.countries,
            "states": z.states,
            "lgas": z.lgas,
            "zone_type": z.zone_type,
            "standard_fee": z.standard_fee, 
            "express_fee": z.express_fee, 
            "eta_text": z.eta_text, 
            "is_active": z.is_active,
            "free_shipping_threshold": z.free_shipping_threshold,
            "weight_fee_per_kg": z.weight_fee_per_kg,
            "volume_fee_per_unit": z.volume_fee_per_unit,
            "min_days": z.min_days,
            "max_days": z.max_days,
            "is_international": z.is_international,
            "customs_handling_fee": z.customs_handling_fee,
            "border_crossing_fee": z.border_crossing_fee,
            "default_carrier": z.default_carrier,
            "auto_assign": z.auto_assign,
        }
        for z in zones
    ]


@router.post("/delivery-zones")
async def create_zone(
    zone_name: str,
    countries: list[str],
    states: list[str],
    lgas: list[str],
    zone_type: str,
    standard_fee: int,
    express_fee: int,
    eta_text: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    zone = DeliveryZone(
        zone_name=zone_name,
        countries=countries,
        states=states,
        lgas=lgas,
        zone_type=zone_type,
        standard_fee=standard_fee,
        express_fee=express_fee,
        eta_text=eta_text,
    )
    db.add(zone)
    await db.flush()
    return {"id": zone.id, "message": "Zone created"}


@router.put("/delivery-zones/{zone_id}")
async def update_zone(zone_id: int, body: DeliveryZoneUpdate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeliveryZone).where(DeliveryZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    for field in ["standard_fee", "express_fee", "eta_text", "is_active", "countries", "states", "lgas", "zone_type", "free_shipping_threshold", "weight_fee_per_kg", "volume_fee_per_unit", "min_days", "max_days", "is_international", "customs_handling_fee", "border_crossing_fee", "default_carrier", "auto_assign"]:
        value = getattr(body, field, None)
        if value is not None:
            setattr(zone, field, value)

    await db.flush()
    return {"message": "Zone updated"}


@router.delete("/delivery-zones/{zone_id}")
async def delete_zone(zone_id: int, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeliveryZone).where(DeliveryZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone.is_active = False
    await db.flush()
    return {"message": "Zone deactivated"}


# --- Bank Accounts ---
@router.get("/bank-accounts")
async def list_bank_accounts(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).order_by(BankAccount.sort_order))
    return [
        {"id": a.id, "bank_name": a.bank_name, "account_name": a.account_name, "account_number": a.account_number, "is_active": a.is_active}
        for a in result.scalars().all()
    ]


@router.post("/bank-accounts")
async def create_bank_account(body: BankAccountCreate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    account = BankAccount(
        bank_name=body.bank_name,
        account_name=body.account_name,
        account_number=body.account_number,
        is_active=body.is_active,
        sort_order=body.sort_order,
    )
    db.add(account)
    await db.flush()
    return {"id": account.id, "message": "Bank account added"}


@router.put("/bank-accounts/{account_id}")
async def update_bank_account(account_id: int, body: BankAccountUpdate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    for field in ["bank_name", "account_name", "account_number", "is_active", "sort_order"]:
        value = getattr(body, field)
        if value is not None:
            setattr(account, field, value)

    await db.flush()
    return {"message": "Bank account updated"}


@router.delete("/bank-accounts/{account_id}")
async def delete_bank_account(account_id: int, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    account.is_active = False
    await db.flush()
    return {"message": "Bank account deactivated"}


# --- Promo Codes ---
@router.get("/promos")
async def list_promos(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PromoCode))
    return [
        {"id": p.id, "code": p.code, "discount_percent": p.discount_percent, "min_order_amount": p.min_order_amount, "max_uses": p.max_uses, "current_uses": p.current_uses, "expires_at": p.expires_at.isoformat() if p.expires_at else None, "is_active": p.is_active}
        for p in result.scalars().all()
    ]


@router.post("/promos")
async def create_promo(body: PromoCreate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from datetime import datetime as _dt
    expires_at = _dt.fromisoformat(body.expires_at) if body.expires_at else None
    promo = PromoCode(
        code=body.code,
        discount_percent=body.discount_percent,
        min_order_amount=body.min_order_amount,
        max_uses=body.max_uses,
        expires_at=expires_at,
        is_active=body.is_active,
    )
    db.add(promo)
    await db.flush()
    return {"id": promo.id, "message": "Promo code created"}


@router.put("/promos/{promo_id}")
async def update_promo(promo_id: int, body: PromoUpdate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from datetime import datetime as _dt
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")

    if body.code is not None:
        promo.code = body.code
    if body.discount_percent is not None:
        promo.discount_percent = body.discount_percent
    if body.min_order_amount is not None:
        promo.min_order_amount = body.min_order_amount
    if body.max_uses is not None:
        promo.max_uses = body.max_uses
    if body.expires_at is not None:
        promo.expires_at = _dt.fromisoformat(body.expires_at)
    if body.is_active is not None:
        promo.is_active = body.is_active

    await db.flush()
    return {"message": "Promo code updated"}


@router.delete("/promos/{promo_id}")
async def delete_promo(promo_id: int, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")

    promo.is_active = False
    await db.flush()
    return {"message": "Promo code deactivated"}


# --- Settings ---
@router.get("/settings")
async def get_settings(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings))
    settings_list = result.scalars().all()
    return {s.key: s.value for s in settings_list}


@router.put("/settings")
async def update_settings(body: dict, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    for key, value in body.items():
        result = await db.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(Settings(key=key, value=value))

    await db.flush()
    return {"message": "Settings updated"}


# --- Homepage Content Management ---
@router.get("/homepage-content")
async def list_homepage_content(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HomepageContent).order_by(HomepageContent.sort_order))
    sections = result.scalars().all()
    return [
        {
            "id": s.id,
            "section": s.section,
            "content": s.content,
            "is_active": s.is_active,
            "sort_order": s.sort_order,
        }
        for s in sections
    ]


@router.get("/homepage-content/{section}")
async def get_homepage_section(section: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HomepageContent).where(HomepageContent.section == section))
    section_data = result.scalar_one_or_none()
    if not section_data:
        raise HTTPException(status_code=404, detail="Section not found")
    
    return {
        "id": section_data.id,
        "section": section_data.section,
        "content": section_data.content,
        "is_active": section_data.is_active,
        "sort_order": section_data.sort_order,
    }


@router.put("/homepage-content/{section}")
async def update_homepage_section(
    section: str,
    content: dict,
    is_active: bool | None = None,
    sort_order: int | None = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HomepageContent).where(HomepageContent.section == section))
    section_data = result.scalar_one_or_none()
    
    if section_data:
        section_data.content = content
        if is_active is not None:
            section_data.is_active = is_active
        if sort_order is not None:
            section_data.sort_order = sort_order
    else:
        # Create new section
        section_data = HomepageContent(
            section=section,
            content=content,
            is_active=is_active if is_active is not None else True,
            sort_order=sort_order if sort_order is not None else 0,
        )
        db.add(section_data)
    
    await db.flush()
    
    # Invalidate homepage cache
    from app.redis import get_redis
    redis = await get_redis()
    if redis:
        await redis.delete("homepage:content")
    
    return {"message": "Section updated"}


@router.post("/homepage-content/initialize")
async def initialize_homepage_content(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    """Initialize default homepage content sections."""
    default_sections = {
        "promo_banner": {
            "enabled": True,
            "text": "Get 15% off your first order — Use code WELCOME15",
            "icon": "sparkles",
            "background": "gradient-warm",
        },
        "hero": {
            "badge": {
                "enabled": True,
                "text": "500+ orders shipped this month",
                "icon": "zap",
            },
            "headline": "Custom souvenirs that leave a lasting impression",
            "subheadline": "Mugs, tees, plaques and more — personalized in bulk with fast turnaround and nationwide delivery.",
            "primary_cta": {
                "text": "Browse products",
                "link": "/shop",
            },
            "secondary_cta": {
                "text": "Track order",
                "link": "/track",
            },
            "trust_signals": [
                {"icon": "truck", "text": "Fast delivery"},
                {"icon": "shield", "text": "Quality guaranteed"},
            ],
        },
        "social_proof": {
            "enabled": True,
            "stats": [
                {"icon": "users", "label": "12,000+", "text": "happy customers"},
                {"icon": "star", "label": "4.9/5", "text": "average rating"},
                {"icon": "truck", "label": "Nationwide", "text": "delivery"},
            ],
        },
        "how_it_works": {
            "enabled": True,
            "steps": [
                {"step": "1", "title": "Choose product", "desc": "Browse our catalog and pick your items"},
                {"step": "2", "title": "Customize", "desc": "Add names, logos, and choose colors"},
                {"step": "3", "title": "Place order", "desc": "Select quantity, delivery, and pay"},
                {"step": "4", "title": "Receive", "desc": "We deliver to your doorstep"},
            ],
        },
        "urgency": {
            "enabled": True,
            "headline": "Limited time offer",
            "text": "Order 100+ items and save up to 30% on unit prices",
            "icon": "clock",
            "background": "gradient-warm",
            "cta": {
                "text": "Shop now",
                "link": "/shop",
            },
        },
        "cta": {
            "enabled": True,
            "headline": "Ready to create custom souvenirs?",
            "text": "Get started with just 10 units. No minimum for samples.",
            "button": {
                "text": "Start your order",
                "link": "/shop",
            },
        },
    }
    
    for section, content in default_sections.items():
        result = await db.execute(select(HomepageContent).where(HomepageContent.section == section))
        existing = result.scalar_one_or_none()
        if not existing:
            db.add(HomepageContent(section=section, content=content))
    
    await db.flush()
    return {"message": "Homepage content initialized"}


# --- Reviews ---
@router.get("/reviews")
async def list_reviews(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).order_by(Review.created_at.desc()))
    return [
        {
            "id": str(r.id), "product_id": str(r.product_id), "author": r.author,
            "rating": r.rating, "title": r.title, "text": r.text,
            "is_verified": r.is_verified, "created_at": r.created_at.isoformat(),
        }
        for r in result.scalars().all()
    ]


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).where(Review.id == uuid.UUID(review_id)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    await db.delete(review)
    await db.flush()
    return {"message": "Review deleted"}


# --- Logo Management ---
@router.get("/logos/pending")
async def list_pending_logos(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    """List all pending logo uploads for admin review."""
    result = await db.execute(
        select(LogoUpload)
        .where(LogoUpload.status == LogoUploadStatus.pending)
        .options(selectinload(LogoUpload.user))
        .order_by(LogoUpload.created_at.desc())
    )
    uploads = result.scalars().all()
    
    return [
        {
            "id": str(upload.id),
            "file_url": upload.file_url,
            "file_name": upload.file_name,
            "file_size": upload.file_size,
            "mime_type": upload.mime_type,
            "user_email": upload.user.email if upload.user else "Unknown",
            "user_name": upload.user.full_name if upload.user else "Unknown",
            "product_id": str(upload.product_id) if upload.product_id else None,
            "order_id": str(upload.order_id) if upload.order_id else None,
            "created_at": upload.created_at.isoformat(),
        }
        for upload in uploads
    ]


@router.post("/logos/{upload_id}/approve")
async def approve_logo(
    upload_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve a logo upload."""
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    
    result = await db.execute(
        select(LogoUpload).where(LogoUpload.id == upload_uuid)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    upload.status = LogoUploadStatus.approved
    upload.reviewed_by = admin.id
    upload.reviewed_at = datetime.now(timezone.utc)
    
    await db.flush()
    
    return {"message": "Logo approved successfully"}


@router.post("/logos/{upload_id}/reject")
async def reject_logo(
    upload_id: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject a logo upload with a reason."""
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    
    result = await db.execute(
        select(LogoUpload).where(LogoUpload.id == upload_uuid)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    upload.status = LogoUploadStatus.rejected
    upload.rejection_reason = body.get("reason", "No reason provided")
    upload.reviewed_by = admin.id
    upload.reviewed_at = datetime.now(timezone.utc)
    
    await db.flush()
    return {"message": "Logo rejected"}


# --- Cart Management ---
@router.get("/carts")
async def list_all_carts(
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with their cart items and cart value."""
    # Get users with cart items
    query = select(User).where(User.role == UserRole.customer.value)
    if search:
        query = query.where(or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    
    query = query.order_by(User.created_at.desc())
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    users = result.scalars().all()
    
    cart_data = []
    for user in users:
        # Get cart items for this user
        cart_result = await db.execute(
            select(CartItem)
            .where(CartItem.user_id == user.id)
            .options(
                selectinload(CartItem.product).selectinload(Product.tiers),
                selectinload(CartItem.variant)
            )
        )
        cart_items = cart_result.scalars().all()
        
        # Calculate cart value
        cart_value = 0
        item_count = 0
        items_data = []
        
        for item in cart_items:
            product = item.product
            variant = item.variant
            base_price = variant.price if variant else product.base_price
            
            # Find best tier price
            unit_price = base_price
            for tier in sorted(product.tiers, key=lambda t: t.min_qty):
                if item.qty >= tier.min_qty:
                    unit_price = tier.unit_price
            
            item_total = unit_price * item.qty
            cart_value += item_total
            item_count += item.qty
            
            items_data.append({
                "id": item.id,
                "productId": str(item.product_id),
                "productName": product.name,
                "qty": item.qty,
                "unitPrice": unit_price,
                "total": item_total,
                "customization": item.customization,
                "variantId": str(item.variant_id) if item.variant_id else None,
                "variantAttributes": variant.attributes if variant else None,
                "logoUrl": item.logo_url,
            })
        
        cart_data.append({
            "userId": str(user.id),
            "userName": user.full_name,
            "userEmail": user.email,
            "userPhone": user.phone,
            "itemCount": item_count,
            "cartValue": cart_value,
            "lastUpdated": max([ci.created_at for ci in cart_items], default=datetime.now(timezone.utc)) if cart_items else None,
            "items": items_data,
        })
    
    return {
        "carts": cart_data,
        "total": len(cart_data),
        "page": page,
        "pages": (len(cart_data) + limit - 1) // limit,
    }


@router.get("/carts/{user_id}")
async def get_user_cart(
    user_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed cart for a specific user."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get cart items
    result = await db.execute(
        select(CartItem)
        .where(CartItem.user_id == user.id)
        .options(
            selectinload(CartItem.product).selectinload(Product.tiers),
            selectinload(CartItem.variant)
        )
    )
    cart_items = result.scalars().all()
    
    return {
        "userId": str(user.id),
        "userName": user.full_name,
        "userEmail": user.email,
        "items": [_cart_item_response(item) for item in cart_items],
    }


@router.delete("/carts/{user_id}")
async def clear_user_cart(
    user_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Clear a user's cart (for abandoned cart recovery)."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    result = await db.execute(select(CartItem).where(CartItem.user_id == user_uuid))
    items = result.scalars().all()
    
    for item in items:
        await db.delete(item)
    
    await db.flush()
    return {"message": "Cart cleared"}


@router.get("/carts/analytics")
async def cart_analytics(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get cart analytics and statistics."""
    from datetime import timedelta
    
    # Total carts with items
    carts_with_items_result = await db.execute(
        select(func.count(func.distinct(CartItem.user_id)))
    )
    total_carts = carts_with_items_result.scalar()
    
    # Total cart value
    cart_value_result = await db.execute(
        select(func.sum(
            # Calculate tier-based pricing for each item
            func.coalesce(
                (Product.base_price * CartItem.qty),
                0
            )
        ))
        .select_from(CartItem)
        .join(Product, CartItem.product_id == Product.id)
    )
    total_cart_value = cart_value_result.scalar() or 0
    
    # Average cart value
    avg_cart_value = total_cart_value / total_carts if total_carts > 0 else 0
    
    # Abandoned carts (carts older than 24 hours without order)
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    abandoned_result = await db.execute(
        select(func.count(func.distinct(CartItem.user_id)))
        .select_from(CartItem)
        .join(User, CartItem.user_id == User.id)
        .where(CartItem.created_at < one_day_ago)
    )
    abandoned_carts = abandoned_result.scalar()
    
    # Most common products in carts
    popular_products_result = await db.execute(
        select(CartItem.product_id, func.count().label('count'))
        .group_by(CartItem.product_id)
        .order_by(func.count().desc())
        .limit(10)
    )
    popular_products = popular_products_result.all()
    
    return {
        "totalCarts": total_carts,
        "totalCartValue": total_cart_value,
        "averageCartValue": int(avg_cart_value),
        "abandonedCarts": abandoned_carts,
        "abandonmentRate": round((abandoned_carts / total_carts * 100) if total_carts > 0 else 0, 2),
        "popularProducts": [
            {"productId": str(p.product_id), "count": p.count}
            for p in popular_products
        ],
    }


# --- Ads Management ---
@router.get("/ads")
async def list_ads(
    position: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all ads with optional filtering."""
    query = select(Ad)
    if position:
        query = query.where(Ad.position == position)
    if is_active is not None:
        query = query.where(Ad.is_active == is_active)
    
    query = query.order_by(Ad.sort_order, Ad.created_at.desc())
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    ads = result.scalars().all()
    
    return [
        {
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "imageUrl": ad.image_url,
            "mobileImageUrl": ad.mobile_image_url,
            "linkUrl": ad.link_url,
            "position": ad.position,
            "isActive": ad.is_active,
            "startDate": ad.start_date.isoformat() if ad.start_date else None,
            "endDate": ad.end_date.isoformat() if ad.end_date else None,
            "sortOrder": ad.sort_order,
            "createdAt": ad.created_at.isoformat(),
            "updatedAt": ad.updated_at.isoformat(),
        }
        for ad in ads
    ]


@router.get("/ads/{ad_id}")
async def get_ad(
    ad_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific ad by ID."""
    result = await db.execute(select(Ad).where(Ad.id == ad_id))
    ad = result.scalar_one_or_none()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    return {
        "id": ad.id,
        "title": ad.title,
        "description": ad.description,
        "imageUrl": ad.image_url,
        "mobileImageUrl": ad.mobile_image_url,
        "linkUrl": ad.link_url,
        "position": ad.position,
        "isActive": ad.is_active,
        "startDate": ad.start_date.isoformat() if ad.start_date else None,
        "endDate": ad.end_date.isoformat() if ad.end_date else None,
        "sortOrder": ad.sort_order,
        "createdAt": ad.created_at.isoformat(),
        "updatedAt": ad.updated_at.isoformat(),
    }


@router.post("/ads")
async def create_ad(
    body: AdCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new ad."""
    ad = Ad(
        title=body.title,
        description=body.description,
        image_url=body.image_url,
        mobile_image_url=body.mobile_image_url,
        link_url=body.link_url,
        position=body.position,
        is_active=body.is_active,
        start_date=body.start_date,
        end_date=body.end_date,
        sort_order=body.sort_order,
    )
    db.add(ad)
    await db.flush()
    
    # Invalidate ads cache
    from app.redis import get_redis
    redis = await get_redis()
    if redis:
        await redis.delete("ads:all")
        await redis.delete(f"ads:{body.position}")
    
    return {"id": ad.id, "message": "Ad created successfully"}


@router.put("/ads/{ad_id}")
async def update_ad(
    ad_id: int,
    body: AdUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing ad."""
    result = await db.execute(select(Ad).where(Ad.id == ad_id))
    ad = result.scalar_one_or_none()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    if body.title is not None:
        ad.title = body.title
    if body.description is not None:
        ad.description = body.description
    if body.image_url is not None:
        ad.image_url = body.image_url
    if body.mobile_image_url is not None:
        ad.mobile_image_url = body.mobile_image_url
    if body.link_url is not None:
        ad.link_url = body.link_url
    if body.position is not None:
        ad.position = body.position
    if body.is_active is not None:
        ad.is_active = body.is_active
    if body.start_date is not None:
        ad.start_date = body.start_date
    if body.end_date is not None:
        ad.end_date = body.end_date
    if body.sort_order is not None:
        ad.sort_order = body.sort_order
    
    await db.flush()
    
    # Invalidate ads cache
    from app.redis import get_redis
    redis = await get_redis()
    if redis:
        await redis.delete("ads:all")
        await redis.delete(f"ads:{ad.position}")
    
    return {"message": "Ad updated successfully"}


@router.delete("/ads/{ad_id}")
async def delete_ad(
    ad_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete an ad."""
    result = await db.execute(select(Ad).where(Ad.id == ad_id))
    ad = result.scalar_one_or_none()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    await db.delete(ad)
    await db.flush()
    
    # Invalidate ads cache
    from app.redis import get_redis
