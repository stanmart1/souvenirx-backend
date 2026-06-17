import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
    DeliveryZoneCreate,
    DeliveryZoneUpdate,
    BankAccountCreate,
    BankAccountUpdate,
    PromoCreate,
    PromoUpdate,
)
from app.services.email import send_email
from app.config import settings

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
    
    from app.redis import cache_delete
    await cache_delete("products:featured", f"product:{product.slug}")

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


@router.post("/products/{product_id}/archive")
async def archive_product(product_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == uuid.UUID(product_id)))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_archived = True
    await db.flush()
    return {"message": "Product archived"}


@router.post("/products/{product_id}/restore")
async def restore_product(product_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == uuid.UUID(product_id)))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_archived = False
    await db.flush()
    return {"message": "Product restored"}


@router.post("/products/{product_id}/duplicate")
async def duplicate_product(product_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Product)
        .where(Product.id == uuid.UUID(product_id))
        .options(
            selectinload(Product.images),
            selectinload(Product.tiers),
            selectinload(Product.customizations),
            selectinload(Product.variants)
        )
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create duplicate
    duplicate = Product(
        slug=f"{original.slug}-copy-{uuid.uuid4().hex[:6]}",
        name=f"{original.name} (Copy)",
        category_id=original.category_id,
        description=original.description,
        base_price=original.base_price,
        moq=original.moq,
        stock=0,  # Start with 0 stock
        is_active=False,  # Start inactive
        tags=original.tags,
        has_variants=original.has_variants,
    )
    db.add(duplicate)
    await db.flush()
    
    # Duplicate images
    for img in original.images:
        db.add(ProductImage(
            product_id=duplicate.id,
            url=img.url,
            sort_order=img.sort_order,
        ))
    
    # Duplicate tiers
    for tier in original.tiers:
        db.add(ProductTier(
            product_id=duplicate.id,
            min_qty=tier.min_qty,
            price=tier.price,
        ))
    
    # Duplicate customizations
    for custom in original.customizations:
        db.add(ProductCustomization(
            product_id=duplicate.id,
            type=custom.type,
            label=custom.label,
            required=custom.required,
            options=custom.options,
        ))
    
    # Duplicate variants
    for variant in original.variants:
        db.add(ProductVariant(
            product_id=duplicate.id,
            sku=f"{variant.sku}-copy-{uuid.uuid4().hex[:6]}",
            attributes=variant.attributes,
            price=variant.price,
            moq=variant.moq,
            stock=0,
            is_active=False,
        ))
    
    await db.flush()
    return {"id": str(duplicate.id), "slug": duplicate.slug, "message": "Product duplicated"}


@router.post("/products/{product_id}/generate-variants")
async def generate_variants(
    product_id: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate variants from attribute matrix.
    Body: {
        "attributes": {
            "Size": ["S", "M", "L", "XL"],
            "Color": ["Red", "Blue", "Green"]
        },
        "base_price": 10000,
        "base_moq": 10,
        "base_stock": 0
    }
    """
    result = await db.execute(select(Product).where(Product.id == uuid.UUID(product_id)))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    attributes = body.get("attributes", {})
    base_price = body.get("base_price", product.base_price)
    base_moq = body.get("base_moq", product.moq)
    base_stock = body.get("base_stock", 0)
    
    if not attributes:
        raise HTTPException(status_code=400, detail="No attributes provided")
    
    # Generate all combinations
    import itertools
    attr_names = list(attributes.keys())
    attr_values = [attributes[name] for name in attr_names]
    combinations = list(itertools.product(*attr_values))
    
    created_count = 0
    for combo in combinations:
        # Build attribute dict
        variant_attrs = {attr_names[i]: combo[i] for i in range(len(attr_names))}
        
        # Generate SKU
        sku_parts = [product.slug] + [str(v).lower().replace(" ", "-") for v in combo]
        sku = "-".join(sku_parts)
        
        # Check if variant already exists
        existing = await db.execute(
            select(ProductVariant).where(ProductVariant.sku == sku)
        )
        if existing.scalar_one_or_none():
            continue  # Skip if already exists
        
        # Create variant
        variant = ProductVariant(
            product_id=product.id,
            sku=sku,
            attributes=variant_attrs,
            price=base_price,
            moq=base_moq,
            stock=base_stock,
            is_active=True,
        )
        db.add(variant)
        created_count += 1
    
    # Mark product as having variants
    product.has_variants = True
    
    await db.flush()
    return {"message": f"Generated {created_count} variants", "total_combinations": len(combinations)}


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


@router.post("/orders/bulk-update-status")
async def bulk_update_order_status(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    order_numbers = body.get("order_numbers", [])
    new_status = body.get("status")
    
    if not order_numbers:
        raise HTTPException(status_code=400, detail="No order numbers provided")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")
    
    # Validate status
    valid_statuses = [s.value for s in OrderStatus]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    result = await db.execute(
        select(Order).where(Order.order_number.in_([on.upper() for on in order_numbers]))
    )
    orders = result.scalars().all()
    
    for order in orders:
        order.status = new_status
        # Add tracking event
        db.add(OrderTracking(
            order_id=order.id,
            status=new_status,
            description=f"Bulk status update by admin to {new_status}"
        ))
    
    await db.flush()
    return {"message": f"Updated {len(orders)} orders to {new_status}"}


@router.get("/orders/{order_number}/invoice")
async def generate_invoice(
    order_number: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate invoice data for an order.
    Frontend will handle PDF generation or printing.
    """
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Order)
        .where(Order.order_number == order_number.upper())
        .options(
            selectinload(Order.items),
            selectinload(Order.user)
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_number": order.order_number,
        "order_date": order.created_at.isoformat(),
        "status": order.status,
        "payment_status": order.payment_status,
        "customer": {
            "name": order.user.full_name,
            "email": order.user.email,
            "phone": order.user.phone,
        },
        "shipping_address": order.shipping_address,
        "items": [
            {
                "product_name": item.product_name,
                "qty": item.qty,
                "unit_price": item.unit_price,
                "total": item.qty * item.unit_price,
            }
            for item in order.items
        ],
        "subtotal": order.subtotal,
        "shipping_fee": order.shipping_fee,
        "total": order.total,
        "notes": order.notes,
    }


@router.get("/orders/{order_number}/packing-slip")
async def generate_packing_slip(
    order_number: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate packing slip data for an order.
    Frontend will handle PDF generation or printing.
    """
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Order)
        .where(Order.order_number == order_number.upper())
        .options(
            selectinload(Order.items),
            selectinload(Order.user)
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_number": order.order_number,
        "order_date": order.created_at.isoformat(),
        "customer": {
            "name": order.user.full_name,
            "phone": order.user.phone,
        },
        "shipping_address": order.shipping_address,
        "items": [
            {
                "product_name": item.product_name,
                "qty": item.qty,
                "sku": item.variant_id or "N/A",
            }
            for item in order.items
        ],
        "notes": order.notes,
    }


@router.get("/orders/{order_number}/timeline")
async def get_order_timeline(
    order_number: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get order timeline/activity log.
    """
    result = await db.execute(select(Order).where(Order.order_number == order_number.upper()))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Fetch tracking events
    tracking_result = await db.execute(
        select(OrderTracking)
        .where(OrderTracking.order_id == order.id)
        .order_by(OrderTracking.created_at.desc())
    )
    tracking_events = tracking_result.scalars().all()
    
    return {
        "order_number": order.order_number,
        "timeline": [
            {
                "id": event.id,
                "status": event.status,
                "description": event.description,
                "created_at": event.created_at.isoformat(),
            }
            for event in tracking_events
        ]
    }


@router.post("/orders/{order_number}/send-email")
async def send_order_email(
    order_number: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Send email to customer about their order.
    Body: { subject: string, message: string }
    """
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Order)
        .where(Order.order_number == order_number.upper())
        .options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    subject = body.get("subject")
    message = body.get("message")
    
    if not subject or not message:
        raise HTTPException(status_code=400, detail="Subject and message are required")

    db.add(OrderTracking(
        order_id=order.id,
        status=order.status,
        description=f"Email sent to customer: {subject}"
    ))

    await db.flush()

    html = (
        f'<div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:600px;margin:0 auto;">'
        f'<h2 style="color:#333;">Message from SouvenirX regarding order {order.order_number}</h2>'
        f'<div style="background:#f9f5f1;border-radius:12px;padding:24px;margin:16px 0;">'
        f'{message}'
        f'</div>'
        f'<p style="color:#888;font-size:13px;">This is an automated message from the SouvenirX support team.</p>'
        f'</div>'
    )
    sent = await send_email(to=order.email, subject=subject, html=html)

    return {
        "message": f"Email {'sent' if sent else 'queued'} to {order.email}",
        "recipient": order.email,
        "subject": subject,
    }


# --- Customers ---
@router.get("/customers")
async def list_customers(
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    date_from: str | None = None,
    date_to: str | None = None,
    min_orders: int | None = None,
    max_orders: int | None = None,
    min_spent: float | None = None,
    max_spent: float | None = None,
    tags: str | None = None,
    email_verified: bool | None = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List customers with advanced filtering support
    
    Query Parameters:
    - search: Search by name or email
    - date_from: Filter by join date (YYYY-MM-DD)
    - date_to: Filter by join date (YYYY-MM-DD)
    - min_orders: Minimum order count
    - max_orders: Maximum order count
    - min_spent: Minimum total spent
    - max_spent: Maximum total spent
    - tags: Filter by tags (comma-separated)
    - email_verified: Filter by email verification status
    """
    from sqlalchemy import func
    from app.models.order import Order
    
    # Base query with order count and total spent
    query = select(
        User,
        func.count(Order.id).label('order_count'),
        func.coalesce(func.sum(Order.total_amount), 0).label('total_spent')
    ).outerjoin(Order, (Order.user_id == User.id) & (Order.status == 'completed'))
    
    # Filter by customer role
    query = query.where(User.role.like('%customer%'))
    
    # Search filter
    if search:
        query = query.where(or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    
    # Date range filter
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.where(User.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            # Add one day to include the entire end date
            to_date = to_date + timedelta(days=1)
            query = query.where(User.created_at < to_date)
        except ValueError:
            pass
    
    # Tags filter
    if tags:
        query = query.where(User.tags.ilike(f"%{tags}%"))
    
    # Email verification filter
    if email_verified is not None:
        query = query.where(User.email_verified == email_verified)
    
    # Group by user
    query = query.group_by(User.id)
    
    # Order count filters (applied after grouping)
    if min_orders is not None:
        query = query.having(func.count(Order.id) >= min_orders)
    
    if max_orders is not None:
        query = query.having(func.count(Order.id) <= max_orders)
    
    # Spending filters (applied after grouping)
    if min_spent is not None:
        query = query.having(func.coalesce(func.sum(Order.total_amount), 0) >= min_spent)
    
    if max_spent is not None:
        query = query.having(func.coalesce(func.sum(Order.total_amount), 0) <= max_spent)
    
    # Order by created date
    query = query.order_by(User.created_at.desc())
    
    # Execute query with pagination
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    rows = result.all()
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(
        select(User.id).where(User.role.like('%customer%')).subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return {
        "customers": [
            {
                "id": str(row.User.id),
                "name": row.User.full_name,
                "email": row.User.email,
                "phone": row.User.phone,
                "joined": row.User.created_at.strftime("%Y-%m-%d"),
                "is_active": row.User.is_active,
                "email_verified": row.User.email_verified,
                "tags": row.User.tags,
                "total_orders": row.order_count,
                "total_spent": float(row.total_spent),
            }
            for row in rows
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        }
    }


@router.get("/customers/{customer_id}")
async def get_customer_detail(
    customer_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(customer_id), User.role.like('%customer%'))
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


@router.patch("/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    body: dict,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update customer information"""
    import re
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(customer_id), User.role.like('%customer%'))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Store old values for audit log
    old_values = {
        "full_name": customer.full_name,
        "email": customer.email,
        "phone": customer.phone,
        "is_active": customer.is_active,
    }
    
    # Update allowed fields with validation
    if "full_name" in body:
        full_name = body["full_name"]
        if not full_name or len(full_name.strip()) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
        customer.full_name = full_name.strip()
    
    if "email" in body:
        email = body["email"]
        # Validate email format
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        # Check if email is already taken
        existing = await db.execute(
            select(User).where(User.email == email, User.id != customer.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        customer.email = email
    
    if "phone" in body:
        phone = body["phone"]
        if phone and not re.match(r"^\+?[0-9\s\-()]{10,20}$", phone):
            raise HTTPException(status_code=400, detail="Invalid phone format")
        customer.phone = phone
    
    if "is_active" in body:
        customer.is_active = body["is_active"]
    
    await db.flush()
    
    # Log changes to audit trail
    changes = {}
    for key in old_values:
        new_value = getattr(customer, key)
        if old_values[key] != new_value:
            changes[key] = {"old": old_values[key], "new": new_value}
    
    if changes:
        await log_audit(
            db=db,
            admin_id=str(admin.id),
            action="update_customer",
            resource_type="user",
            resource_id=customer_id,
            changes=changes,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    
    return {"message": "Customer updated", "id": str(customer.id)}


@router.get("/customers/{customer_id}/notes")
async def get_customer_notes(
    customer_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all notes for a customer"""
    from app.models.customer_note import CustomerNote
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(CustomerNote)
        .where(CustomerNote.customer_id == uuid.UUID(customer_id))
        .options(selectinload(CustomerNote.admin))
        .order_by(CustomerNote.created_at.desc())
    )
    notes = result.scalars().all()
    
    return {
        "notes": [
            {
                "id": note.id,
                "note": note.note,
                "admin_name": note.admin.full_name if note.admin else "System",
                "created_at": note.created_at.isoformat(),
            }
            for note in notes
        ]
    }


@router.post("/customers/{customer_id}/notes")
async def add_customer_note(
    customer_id: str,
    body: dict,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Add a note to a customer"""
    from app.models.customer_note import CustomerNote
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    
    # Verify customer exists
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(customer_id), User.role.like('%customer%'))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Customer not found")
    
    note_text = body.get("note")
    if not note_text:
        raise HTTPException(status_code=400, detail="Note text is required")
    
    # Validate note length (max 1000 characters)
    if len(note_text) > 1000:
        raise HTTPException(status_code=400, detail="Note must be 1000 characters or less")
    
    note = CustomerNote(
        customer_id=uuid.UUID(customer_id),
        admin_id=admin.id,
        note=note_text,
    )
    db.add(note)
    await db.flush()
    
    # Log audit trail
    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="add_customer_note",
        resource_type="user",
        resource_id=customer_id,
        changes={"note_id": note.id, "note_preview": note_text[:100]},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return {"message": "Note added", "id": note.id}


@router.delete("/customers/{customer_id}/notes/{note_id}")
async def delete_customer_note(
    customer_id: str,
    note_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a customer note"""
    from app.models.customer_note import CustomerNote
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    
    result = await db.execute(
        select(CustomerNote).where(
            CustomerNote.id == note_id,
            CustomerNote.customer_id == uuid.UUID(customer_id)
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Store note content for audit log
    note_content = note.note
    
    await db.delete(note)
    await db.flush()
    
    # Log audit trail
    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="delete_customer_note",
        resource_type="user",
        resource_id=customer_id,
        changes={"note_id": note_id, "deleted_note": note_content[:100]},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return {"message": "Note deleted"}


@router.get("/customers/{customer_id}/ltv")
async def calculate_customer_ltv(
    customer_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Calculate customer lifetime value and metrics using aggregation"""
    from sqlalchemy import func, case
    from datetime import timedelta
    
    customer_uuid = uuid.UUID(customer_id)
    
    # Verify customer exists
    result = await db.execute(
        select(User).where(User.id == customer_uuid, User.role.like('%customer%'))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Use aggregation to calculate metrics efficiently (no loading all orders)
    stats_result = await db.execute(
        select(
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total).label("total_spent"),
            func.min(Order.created_at).label("first_order_date"),
            func.max(Order.created_at).label("last_order_date"),
        )
        .where(
            Order.user_id == customer_uuid,
            Order.payment_status == PaymentStatus.success.value
        )
    )
    stats = stats_result.one()
    
    total_orders = stats.total_orders or 0
    total_spent = stats.total_spent or 0
    first_order_date = stats.first_order_date
    last_order_date = stats.last_order_date
    
    if total_orders == 0:
        return {
            "ltv": 0,
            "total_orders": 0,
            "avg_order_value": 0,
            "first_order_date": None,
            "last_order_date": None,
            "customer_lifetime_days": 0,
            "purchase_frequency": 0,
        }
    
    lifetime_days = (datetime.now(timezone.utc) - first_order_date).days if first_order_date else 0
    
    return {
        "ltv": int(total_spent),
        "total_orders": total_orders,
        "avg_order_value": int(total_spent / total_orders),
        "first_order_date": first_order_date.isoformat() if first_order_date else None,
        "last_order_date": last_order_date.isoformat() if last_order_date else None,
        "customer_lifetime_days": lifetime_days,
        "purchase_frequency": total_orders / max(lifetime_days / 30, 1) if lifetime_days > 0 else 0,
    }


@router.patch("/customers/{customer_id}/tags")
async def update_customer_tags(
    customer_id: str,
    body: dict,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update customer tags for segmentation"""
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(customer_id), User.role.like('%customer%'))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    old_tags = customer.tags
    tags = body.get("tags", "")
    customer.tags = tags
    
    await db.flush()
    
    # Log audit trail if tags changed
    if old_tags != tags:
        await log_audit(
            db=db,
            admin_id=str(admin.id),
            action="update_customer_tags",
            resource_type="user",
            resource_id=customer_id,
            changes={"old_tags": old_tags, "new_tags": tags},
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    
    return {"message": "Tags updated", "tags": tags}


@router.post("/customers/{customer_id}/reset-password")
async def admin_reset_customer_password(
    customer_id: str,
    body: dict,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin resets customer password"""
    from app.services.auth import hash_password
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(customer_id))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    new_password = body.get("new_password")
    if not new_password:
        raise HTTPException(status_code=400, detail="New password is required")
    
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Update password
    customer.password_hash = hash_password(new_password)
    await db.flush()
    
    # Log audit trail
    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="reset_password",
        resource_type="user",
        resource_id=customer_id,
        changes={"reset_by_admin": admin.full_name},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    # Send email notification to customer
    try:
        from app.services.email import send_templated_email
        await send_templated_email(
            template_name="password_reset_by_admin",
            to_email=customer.email,
            variables={
                "customer_name": customer.full_name,
                "admin_name": admin.full_name,
            },
            db=db
        )
    except Exception as e:
        print(f"Failed to send password reset notification email: {e}")
        # Don't fail the request if email fails
    
    return {"message": "Password reset successfully"}


@router.get("/customers/export")
async def export_customers_csv(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Export customer list as CSV with streaming for large datasets"""
    import csv
    from fastapi.responses import StreamingResponse
    from sqlalchemy import func
    
    async def generate_csv():
        """Generator function for streaming CSV data"""
        # Yield CSV header
        yield "ID,Name,Email,Phone,Tags,Status,Joined,Total Orders,Total Spent (NGN),Email Verified\n"
        
        # Stream customers in batches of 100
        batch_size = 100
        offset = 0
        
        while True:
            # Get batch of customers with order stats
            result = await db.execute(
                select(
                    User.id,
                    User.full_name,
                    User.email,
                    User.phone,
                    User.tags,
                    User.is_active,
                    User.email_verified,
                    User.created_at,
                    func.count(Order.id).label("total_orders"),
                    func.coalesce(func.sum(Order.total), 0).label("total_spent"),
                )
                .outerjoin(Order, (Order.user_id == User.id) & (Order.payment_status == PaymentStatus.success.value))
                .where(User.role.like('%customer%'))
                .group_by(User.id)
                .order_by(User.created_at.desc())
                .offset(offset)
                .limit(batch_size)
            )
            customers = result.all()
            
            if not customers:
                break
            
            # Yield each customer row
            for customer in customers:
                # Escape fields that might contain commas or quotes
                _name = customer.full_name or ""
                name = '"' + _name.replace('"', '""') + '"' if ',' in _name or '"' in _name else _name
                email = customer.email
                phone = customer.phone or ""
                _tags = customer.tags or ""
                tags = '"' + _tags.replace('"', '""') + '"' if ',' in _tags or '"' in _tags else _tags
                status = "Active" if customer.is_active else "Inactive"
                joined = customer.created_at.strftime("%Y-%m-%d")
                total_orders = customer.total_orders
                total_spent = customer.total_spent / 100  # Convert from kobo to naira
                email_verified = "Yes" if customer.email_verified else "No"
                
                yield f'{customer.id},{name},{email},{phone},{tags},{status},{joined},{total_orders},{total_spent:.2f},{email_verified}\n'
            
            offset += batch_size
    
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers_export.csv"}
    )


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


@router.get("/affiliates/{affiliate_id}/payouts")
async def get_affiliate_payouts(
    affiliate_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get payout history for an affiliate"""
    result = await db.execute(
        select(AffiliatePayout)
        .where(AffiliatePayout.affiliate_id == uuid.UUID(affiliate_id))
        .order_by(AffiliatePayout.created_at.desc())
    )
    payouts = result.scalars().all()
    
    return {
        "payouts": [
            {
                "id": str(p.id),
                "amount": p.amount,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "processed_at": p.processed_at.isoformat() if p.processed_at else None,
            }
            for p in payouts
        ]
    }


@router.get("/affiliates/payouts/all")
async def get_all_payouts(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all affiliate payouts with affiliate info"""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(AffiliatePayout)
        .options(selectinload(AffiliatePayout.affiliate).selectinload(Affiliate.user))
        .order_by(AffiliatePayout.created_at.desc())
        .limit(100)
    )
    payouts = result.scalars().all()
    
    return {
        "payouts": [
            {
                "id": str(p.id),
                "affiliate_id": str(p.affiliate_id),
                "affiliate_name": p.affiliate.user.full_name if p.affiliate and p.affiliate.user else "Unknown",
                "amount": p.amount,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "processed_at": p.processed_at.isoformat() if p.processed_at else None,
            }
            for p in payouts
        ]
    }


@router.patch("/affiliates/{affiliate_id}/commission-rate")
async def update_commission_rate(
    affiliate_id: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update commission rate for a specific affiliate"""
    result = await db.execute(select(Affiliate).where(Affiliate.id == uuid.UUID(affiliate_id)))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    
    commission_rate = body.get("commission_rate")
    if commission_rate is None or commission_rate < 0 or commission_rate > 1:
        raise HTTPException(status_code=400, detail="Commission rate must be between 0 and 1")
    
    affiliate.commission_rate = commission_rate
    await db.flush()
    
    return {"message": "Commission rate updated", "commission_rate": commission_rate}


@router.get("/affiliates/{affiliate_id}/referral-link")
async def generate_referral_link(
    affiliate_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generate referral link for an affiliate"""
    result = await db.execute(select(Affiliate).where(Affiliate.id == uuid.UUID(affiliate_id)))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    
    # Get base URL from settings
    base_url = settings.frontend_url.rstrip("/")
    referral_link = f"{base_url}?ref={affiliate.referral_code}"
    
    return {
        "referral_code": affiliate.referral_code,
        "referral_link": referral_link,
        "short_link": f"{base_url}/r/{affiliate.referral_code}",
    }


@router.get("/affiliates/leaderboard")
async def get_affiliate_leaderboard(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get affiliate performance leaderboard"""
    from sqlalchemy import func
    from sqlalchemy.orm import selectinload
    
    # Get affiliates with their stats
    result = await db.execute(
        select(
            Affiliate,
            func.count(AffiliateClick.id).label("total_clicks"),
            func.count(AffiliateConversion.id).label("total_conversions"),
        )
        .outerjoin(AffiliateClick, AffiliateClick.affiliate_id == Affiliate.id)
        .outerjoin(AffiliateConversion, AffiliateConversion.affiliate_id == Affiliate.id)
        .options(selectinload(Affiliate.user))
        .group_by(Affiliate.id)
        .order_by(Affiliate.total_earnings.desc())
        .limit(50)
    )
    affiliates_data = result.all()
    
    leaderboard = []
    for idx, (affiliate, total_clicks, total_conversions) in enumerate(affiliates_data, 1):
        conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        
        leaderboard.append({
            "rank": idx,
            "id": str(affiliate.id),
            "name": affiliate.user.full_name if affiliate.user else "Unknown",
            "referral_code": affiliate.referral_code,
            "total_earnings": affiliate.total_earnings,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "conversion_rate": round(conversion_rate, 2),
            "commission_rate": affiliate.commission_rate,
        })
    
    return {"leaderboard": leaderboard}


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
async def create_zone(body: DeliveryZoneCreate, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    zone = DeliveryZone(
        zone_name=body.zone_name,
        countries=body.countries,
        states=body.states,
        lgas=body.lgas,
        zone_type=body.zone_type,
        standard_fee=body.standard_fee,
        express_fee=body.express_fee,
        eta_text=body.eta_text,
        is_active=body.is_active,
        free_shipping_threshold=body.free_shipping_threshold,
        weight_fee_per_kg=body.weight_fee_per_kg,
        volume_fee_per_unit=body.volume_fee_per_unit,
        min_days=body.min_days,
        max_days=body.max_days,
        is_international=body.is_international,
        customs_handling_fee=body.customs_handling_fee,
        border_crossing_fee=body.border_crossing_fee,
        default_carrier=body.default_carrier,
        auto_assign=body.auto_assign,
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


@router.get("/bank-accounts/nigerian-banks")
async def get_nigerian_banks(admin: User = Depends(get_current_admin)):
    """Get list of Nigerian banks for dropdown"""
    # Common Nigerian banks with their Paystack codes
    banks = [
        {"name": "Access Bank", "code": "044"},
        {"name": "Citibank Nigeria", "code": "023"},
        {"name": "Ecobank Nigeria", "code": "050"},
        {"name": "Fidelity Bank", "code": "070"},
        {"name": "First Bank of Nigeria", "code": "011"},
        {"name": "First City Monument Bank", "code": "214"},
        {"name": "Guaranty Trust Bank", "code": "058"},
        {"name": "Heritage Bank", "code": "030"},
        {"name": "Keystone Bank", "code": "082"},
        {"name": "Polaris Bank", "code": "076"},
        {"name": "Providus Bank", "code": "101"},
        {"name": "Stanbic IBTC Bank", "code": "221"},
        {"name": "Standard Chartered Bank", "code": "068"},
        {"name": "Sterling Bank", "code": "232"},
        {"name": "Union Bank of Nigeria", "code": "032"},
        {"name": "United Bank for Africa", "code": "033"},
        {"name": "Unity Bank", "code": "215"},
        {"name": "Wema Bank", "code": "035"},
        {"name": "Zenith Bank", "code": "057"},
    ]
    return {"banks": banks}


@router.post("/bank-accounts/{account_id}/verify")
async def verify_bank_account(
    account_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Verify bank account with Paystack"""
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    if not account.account_number or len(account.account_number) != 10:
        raise HTTPException(status_code=400, detail="Invalid account number format (must be 10 digits)")

    if not account.bank_code:
        raise HTTPException(status_code=400, detail="Bank code required for verification")

    if not settings.paystack_secret_key:
        raise HTTPException(status_code=503, detail="Paystack is not configured. Set PAYSTACK_SECRET_KEY.")

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.paystack.co/bank/resolve",
                params={
                    "account_number": account.account_number,
                    "bank_code": account.bank_code,
                },
                headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("message", "Paystack verification failed") if e.response else "Paystack API error"
        raise HTTPException(status_code=400, detail=f"Paystack verification failed: {detail}")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach Paystack API")

    if not data.get("status"):
        raise HTTPException(status_code=400, detail=data.get("message", "Account could not be resolved"))

    resolved_name = data["data"].get("account_name", "")
    account.account_name = resolved_name
    account.is_verified = True
    await db.flush()

    return {
        "message": "Account verified successfully",
        "account_name": resolved_name,
        "account_number": account.account_number,
        "is_verified": True,
    }


@router.post("/bank-accounts/reorder")
async def reorder_bank_accounts(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reorder bank accounts (drag-drop sort)"""
    account_ids = body.get("account_ids", [])
    
    if not account_ids:
        raise HTTPException(status_code=400, detail="account_ids required")
    
    # Update sort_order for each account
    for index, account_id in enumerate(account_ids):
        result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
        account = result.scalar_one_or_none()
        if account:
            account.sort_order = index
    
    await db.flush()
    return {"message": "Bank accounts reordered"}


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


@router.get("/promos/{promo_id}/analytics")
async def get_promo_analytics(
    promo_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get usage analytics for a promo code"""
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    
    return {
        "code": promo.code,
        "times_used": promo.current_uses,
        "max_uses": promo.max_uses,
        "usage_percentage": (promo.current_uses / promo.max_uses * 100) if promo.max_uses else 0,
        "total_revenue_impact": promo.total_revenue_impact,
        "discount_percent": promo.discount_percent,
        "is_active": promo.is_active,
        "is_stackable": promo.is_stackable,
        "created_at": promo.created_at.isoformat(),
        "expires_at": promo.expires_at.isoformat() if promo.expires_at else None,
    }


@router.post("/promos/{promo_id}/duplicate")
async def duplicate_promo(
    promo_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate an existing promo code"""
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Promo code not found")
    
    # Generate new code
    import random
    import string
    new_code = f"{original.code}_COPY_{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"
    
    # Create duplicate
    duplicate = PromoCode(
        code=new_code,
        discount_percent=original.discount_percent,
        min_order_amount=original.min_order_amount,
        max_uses=original.max_uses,
        expires_at=original.expires_at,
        is_active=False,  # Start as inactive
        is_stackable=original.is_stackable,
    )
    db.add(duplicate)
    await db.flush()
    
    return {
        "id": duplicate.id,
        "code": duplicate.code,
        "message": "Promo code duplicated successfully",
    }


@router.post("/promos/generate-code")
async def generate_promo_code(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generate a random promo code"""
    import random
    import string
    
    prefix = body.get("prefix", "PROMO")
    length = body.get("length", 8)
    
    if length < 4 or length > 20:
        raise HTTPException(status_code=400, detail="Length must be between 4 and 20")
    
    # Generate random code
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    code = f"{prefix}{random_part}"
    
    # Check if code already exists
    result = await db.execute(select(PromoCode).where(PromoCode.code == code))
    if result.scalar_one_or_none():
        # Try again with different random part
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        code = f"{prefix}{random_part}"
    
    return {"code": code}


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
    
    from app.redis import cache_delete
    await cache_delete("homepage:content")

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
            "is_verified": r.is_verified, "is_approved": r.is_approved,
            "is_featured": r.is_featured, "admin_reply": r.admin_reply,
            "admin_reply_at": r.admin_reply_at.isoformat() if r.admin_reply_at else None,
            "created_at": r.created_at.isoformat(),
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


@router.post("/logos/bulk-approve")
async def bulk_approve_logos(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bulk approve logo uploads"""
    upload_ids = body.get("upload_ids", [])
    
    if not upload_ids:
        raise HTTPException(status_code=400, detail="upload_ids required")
    
    count = 0
    for upload_id in upload_ids:
        try:
            upload_uuid = uuid.UUID(upload_id)
            result = await db.execute(select(LogoUpload).where(LogoUpload.id == upload_uuid))
            upload = result.scalar_one_or_none()
            
            if upload:
                upload.status = LogoUploadStatus.approved
                upload.reviewed_by = admin.id
                upload.reviewed_at = datetime.now(timezone.utc)
                count += 1
        except ValueError:
            continue
    
    await db.flush()
    return {"message": f"{count} logos approved"}


@router.post("/logos/bulk-reject")
async def bulk_reject_logos(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bulk reject logo uploads"""
    upload_ids = body.get("upload_ids", [])
    reason = body.get("reason", "Bulk rejection")
    
    if not upload_ids:
        raise HTTPException(status_code=400, detail="upload_ids required")
    
    count = 0
    for upload_id in upload_ids:
        try:
            upload_uuid = uuid.UUID(upload_id)
            result = await db.execute(select(LogoUpload).where(LogoUpload.id == upload_uuid))
            upload = result.scalar_one_or_none()
            
            if upload:
                upload.status = LogoUploadStatus.rejected
                upload.rejection_reason = reason
                upload.reviewed_by = admin.id
                upload.reviewed_at = datetime.now(timezone.utc)
                count += 1
        except ValueError:
            continue
    
    await db.flush()
    return {"message": f"{count} logos rejected"}


@router.get("/logos/{upload_id}/download")
async def download_logo(
    upload_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get download URL for original logo"""
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    
    result = await db.execute(select(LogoUpload).where(LogoUpload.id == upload_uuid))
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return {
        "file_url": upload.file_url,
        "file_name": upload.file_name,
        "mime_type": upload.mime_type,
    }



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
    
    from app.redis import cache_delete
    await cache_delete("ads:all", f"ads:{body.position}")

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
    
    from app.redis import cache_delete
    await cache_delete("ads:all", f"ads:{ad.position}")

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

    from app.redis import cache_delete
    await cache_delete("ads:all", f"ads:{ad.position}")

    return {"message": "Ad deleted successfully"}


@router.get("/ads/{ad_id}/analytics")
async def get_ad_analytics(
    ad_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics for an ad"""
    result = await db.execute(select(Ad).where(Ad.id == ad_id))
    ad = result.scalar_one_or_none()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    ctr = (ad.clicks / ad.impressions * 100) if ad.impressions > 0 else 0
    
    return {
        "id": ad.id,
        "title": ad.title,
        "impressions": ad.impressions,
        "clicks": ad.clicks,
        "ctr": round(ctr, 2),
        "variant": ad.variant,
        "is_active": ad.is_active,
        "start_date": ad.start_date.isoformat() if ad.start_date else None,
        "end_date": ad.end_date.isoformat() if ad.end_date else None,
    }


@router.post("/ads/{ad_id}/track-impression")
async def track_ad_impression(
    ad_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Track ad impression (public endpoint)"""
    result = await db.execute(select(Ad).where(Ad.id == ad_id))
    ad = result.scalar_one_or_none()
    if not ad:
        return {"message": "Ad not found"}
    
    ad.impressions += 1
    await db.flush()
    return {"message": "Impression tracked"}


@router.post("/ads/{ad_id}/track-click")
async def track_ad_click(
    ad_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Track ad click (public endpoint)"""
    result = await db.execute(select(Ad).where(Ad.id == ad_id))
    ad = result.scalar_one_or_none()
    if not ad:
        return {"message": "Ad not found"}
    
    ad.clicks += 1
    await db.flush()
    return {"message": "Click tracked"}


# --- User Management ---
@router.get("/users")
async def list_all_users(
    search: str | None = None,
    role_filter: str | None = None,  # "customer", "affiliate", "admin"
    is_active: bool | None = None,
    email_verified: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with optional filtering"""
    query = select(User)
    
    if search:
        query = query.where(
            or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )
    
    if role_filter:
        query = query.where(User.role.like(f"%{role_filter}%"))
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    if email_verified is not None:
        query = query.where(User.email_verified == email_verified)
    
    query = query.order_by(User.created_at.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(User)
    if search:
        count_query = count_query.where(
            or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )
    if role_filter:
        count_query = count_query.where(User.role.like(f"%{role_filter}%"))
    if is_active is not None:
        count_query = count_query.where(User.is_active == is_active)
    if email_verified is not None:
        count_query = count_query.where(User.email_verified == email_verified)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    users = result.scalars().all()
    
    return {
        "users": [
            {
                "id": str(u.id),
                "name": u.full_name,
                "email": u.email,
                "phone": u.phone,
                "roles": u.get_roles(),
                "active_role": u.active_role,
                "joined": u.created_at.strftime("%Y-%m-%d"),
                "is_active": u.is_active,
                "email_verified": u.email_verified,
                "tags": u.tags,
            }
            for u in users
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    }


@router.patch("/users/{user_id}/roles")
async def update_user_roles(
    user_id: str,
    body: dict,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user roles"""
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_roles = body.get("roles", [])
    valid_roles = ["customer", "affiliate", "admin"]
    
    if not new_roles:
        raise HTTPException(status_code=400, detail="At least one role is required")
    
    if not all(r in valid_roles for r in new_roles):
        raise HTTPException(status_code=400, detail=f"Invalid role. Valid roles: {', '.join(valid_roles)}")
    
    # Prevent removing admin role from yourself
    if str(user.id) == str(admin.id) and "admin" not in new_roles:
        raise HTTPException(status_code=400, detail="Cannot remove admin role from your own account")
    
    old_roles = user.get_roles()
    user.role = ",".join(new_roles)
    
    # If active_role is no longer in roles, reset it to first role
    if user.active_role and user.active_role not in new_roles:
        user.active_role = new_roles[0]
    
    await db.flush()
    
    # Log audit trail
    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="update_roles",
        resource_type="user",
        resource_id=user_id,
        changes={"old_roles": old_roles, "new_roles": new_roles},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return {"message": "Roles updated successfully", "roles": new_roles}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    permanent: bool = Query(False, description="Permanently delete user (super-admin only)"),
    request: Request = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete (deactivate) or hard delete user"""
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if str(user.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    if permanent:
        # Hard delete - requires admin role
        if not admin.has_role("admin"):
            raise HTTPException(status_code=403, detail="Super admin permission required for permanent deletion")
        
        # Store user info for audit log before deletion
        user_info = {
            "email": user.email,
            "name": user.full_name,
            "roles": user.get_roles(),
        }
        
        await db.delete(user)
        await db.flush()
        
        # Log audit trail
        await log_audit(
            db=db,
            admin_id=str(admin.id),
            action="hard_delete_user",
            resource_type="user",
            resource_id=user_id,
            changes={"deleted_user": user_info},
            ip_address=get_client_ip(request) if request else None,
            user_agent=get_user_agent(request) if request else None,
        )
        
        return {"message": "User permanently deleted"}
    else:
        # Soft delete - deactivate and anonymize email
        old_email = user.email
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.local"
        
        await db.flush()
        
        # Log audit trail
        await log_audit(
            db=db,
            admin_id=str(admin.id),
            action="soft_delete_user",
            resource_type="user",
            resource_id=user_id,
            changes={"old_email": old_email, "deactivated": True},
            ip_address=get_client_ip(request) if request else None,
            user_agent=get_user_agent(request) if request else None,
        )
        
        return {"message": "User deactivated successfully"}


@router.post("/users/{user_id}/verify-email")
async def admin_verify_user_email(
    user_id: str,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin manually verifies user email"""
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    await db.flush()
    
    # Log audit trail
    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="verify_email",
        resource_type="user",
        resource_id=user_id,
        changes={"verified_by_admin": admin.full_name},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return {"message": "Email verified successfully"}


@router.post("/users/bulk-update")
async def bulk_update_users(
    body: dict,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk update users.
    
    Supported actions:
    - activate: Set is_active=True
    - deactivate: Set is_active=False
    - add_tag: Add a tag to users
    - remove_tag: Remove a tag from users
    - verify_email: Manually verify emails
    """
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    from sqlalchemy import update as sql_update
    
    user_ids_str = body.get("user_ids", [])
    action = body.get("action")
    value = body.get("value")  # Used for add_tag/remove_tag
    
    if not user_ids_str:
        raise HTTPException(status_code=400, detail="No users selected")
    
    if not action:
        raise HTTPException(status_code=400, detail="Action is required")
    
    try:
        user_ids = [uuid.UUID(id) for id in user_ids_str]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    # Prevent bulk operations on yourself
    if str(admin.id) in user_ids_str:
        raise HTTPException(status_code=400, detail="Cannot perform bulk operations on your own account")
    
    if action == "activate":
        await db.execute(
            sql_update(User).where(User.id.in_(user_ids)).values(is_active=True)
        )
        await db.flush()
        
    elif action == "deactivate":
        await db.execute(
            sql_update(User).where(User.id.in_(user_ids)).values(is_active=False)
        )
        await db.flush()
        
    elif action == "verify_email":
        await db.execute(
            sql_update(User)
            .where(User.id.in_(user_ids))
            .values(
                email_verified=True,
                verification_token=None,
                verification_token_expires_at=None
            )
        )
        await db.flush()
        
    elif action == "add_tag":
        if not value:
            raise HTTPException(status_code=400, detail="Tag value is required for add_tag action")
        
        # Fetch users and update tags individually
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = result.scalars().all()
        
        for user in users:
            existing_tags = [t.strip() for t in user.tags.split(",") if t.strip()] if user.tags else []
            if value not in existing_tags:
                existing_tags.append(value)
                user.tags = ",".join(existing_tags)
        
        await db.flush()
        
    elif action == "remove_tag":
        if not value:
            raise HTTPException(status_code=400, detail="Tag value is required for remove_tag action")
        
        # Fetch users and update tags individually
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = result.scalars().all()
        
        for user in users:
            existing_tags = [t.strip() for t in user.tags.split(",") if t.strip()] if user.tags else []
            if value in existing_tags:
                existing_tags.remove(value)
                user.tags = ",".join(existing_tags) if existing_tags else ""
        
        await db.flush()
        
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    # Log audit trail
    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action=f"bulk_{action}",
        resource_type="user",
        resource_id=",".join(str(id) for id in user_ids),
        changes={"action": action, "value": value, "count": len(user_ids)},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return {"message": f"{len(user_ids)} users updated successfully", "action": action}


# --- Customer Impersonation ---
@router.post("/customers/{customer_id}/impersonate")
async def impersonate_customer(
    customer_id: str,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Impersonate a customer to view the site as they would see it.
    Creates a temporary session token that allows admin to act as the customer.
    """
    from app.services.audit import log_audit, get_client_ip, get_user_agent
    
    # Get customer
    result = await db.execute(select(User).where(User.id == customer_id))
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Prevent impersonating other admins
    if "admin" in customer.role:
        raise HTTPException(status_code=403, detail="Cannot impersonate admin users")
    
    # Create impersonation token (JWT with special claim)
    from datetime import datetime, timedelta
    import jwt
    from app.config import settings
    
    # Token expires in 1 hour
    expiration = datetime.utcnow() + timedelta(hours=1)
    
    token_data = {
        "sub": str(customer.id),
        "impersonated_by": str(admin.id),
        "impersonator_name": admin.full_name,
        "impersonator_email": admin.email,
        "exp": expiration,
        "type": "impersonation"
    }
    
    impersonation_token = jwt.encode(token_data, settings.jwt_secret, algorithm="HS256")
    
    # Log the impersonation
    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="impersonate_customer",
        resource_type="user",
        resource_id=customer_id,
        changes={"impersonated_user": customer.email, "impersonator": admin.email},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return {
        "impersonation_token": impersonation_token,
        "customer": {
            "id": str(customer.id),
            "name": customer.full_name,
            "email": customer.email,
        },
        "expires_at": expiration.isoformat(),
        "message": f"Now impersonating {customer.full_name}. Token expires in 1 hour."
    }


@router.post("/customers/stop-impersonation")
async def stop_impersonation(
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Stop impersonating a customer and return to admin session.
    """
    from app.services.audit import log_audit
    
    # Log the stop impersonation
    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="stop_impersonation",
        resource_type="user",
        resource_id=str(admin.id),
        changes={"admin": admin.email},
        request=request,
    )
    
    return {"message": "Impersonation stopped"}


# --- Audit Logs ---
@router.get("/audit-logs")
async def list_audit_logs(
    resource_type: str | None = None,
    resource_id: str | None = None,
    admin_id: str | None = None,
    action: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List audit logs with optional filtering.
    
    Filters:
    - resource_type: Filter by resource type (e.g., "user", "order")
    - resource_id: Filter by specific resource ID
    - admin_id: Filter by admin who performed the action
    - action: Filter by action type (e.g., "update_customer", "reset_password")
    - start_date: Filter logs from this date (ISO format: YYYY-MM-DD)
    - end_date: Filter logs until this date (ISO format: YYYY-MM-DD)
    """
    from app.models.audit_log import AuditLog
    import json
    
    query = select(AuditLog).options(selectinload(AuditLog.admin))
    
    # Apply filters
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)
    
    if admin_id:
        try:
            query = query.where(AuditLog.admin_id == uuid.UUID(admin_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid admin_id format")
    
    if action:
        query = query.where(AuditLog.action == action)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            query = query.where(AuditLog.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            query = query.where(AuditLog.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    # Order by most recent first
    query = query.order_by(AuditLog.created_at.desc())
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(AuditLog)
    if resource_type:
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        count_query = count_query.where(AuditLog.resource_id == resource_id)
    if admin_id:
        count_query = count_query.where(AuditLog.admin_id == uuid.UUID(admin_id))
    if action:
        count_query = count_query.where(AuditLog.action == action)
    if start_date:
        count_query = count_query.where(AuditLog.created_at >= start_dt)
    if end_date:
        count_query = count_query.where(AuditLog.created_at <= end_dt)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    logs = result.scalars().all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "admin_id": str(log.admin_id) if log.admin_id else None,
                "admin_name": log.admin.full_name if log.admin else "System",
                "admin_email": log.admin.email if log.admin else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "changes": json.loads(log.changes) if log.changes else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    }
