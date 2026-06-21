import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_optional_user
from app.models.product import Product, Category, ProductImage, ProductTier, ProductCustomization, ProductVariant, ProductGroup
from app.models.review import Review
from app.models.settings import HomepageContent, Ad
from app.schemas.product import ReviewCreate

router = APIRouter()


async def invalidate_product_cache(slug: str):
    """Helper to invalidate product-related caches."""
    from app.redis import cache_delete
    await cache_delete(f"product:{slug}", "products:featured")


@router.get("/homepage-content")
async def get_homepage_content(db: AsyncSession = Depends(get_db)):
    """Public endpoint to fetch homepage content with caching."""
    from app.redis import cache_get, cache_set

    cached = await cache_get("homepage:content")
    if cached is not None:
        return cached

    result = await db.execute(
        select(HomepageContent)
        .where(HomepageContent.is_active == True)
        .order_by(HomepageContent.sort_order)
    )
    sections = result.scalars().all()

    content_dict = {}
    for section in sections:
        content_dict[section.section] = section.content

    await cache_set("homepage:content", content_dict, ex=300)
    return content_dict


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List categories with caching."""
    from app.redis import cache_get, cache_set

    cached = await cache_get("categories:list")
    if cached is not None:
        return cached

    result = await db.execute(select(Category).order_by(Category.sort_order))
    cats = result.scalars().all()
    response = [{"id": c.id, "slug": c.slug, "name": c.name, "icon": c.icon, "image": c.image, "description": c.description} for c in cats]

    await cache_set("categories:list", response, ex=600)
    
    return response


@router.get("/featured")
async def featured_products(db: AsyncSession = Depends(get_db)):
    """Featured products with caching."""
    from app.redis import cache_get, cache_set

    cached = await cache_get("products:featured")
    if cached is not None:
        return cached

    result = await db.execute(
        select(Product)
        .where(Product.is_active == True)
        .options(
            selectinload(Product.images),
            selectinload(Product.tiers),
            selectinload(Product.customizations),
            selectinload(Product.category),
        )
        .order_by(Product.rating.desc())
        .limit(4)
    )
    products = result.scalars().all()
    response = [_product_response(p) for p in products]

    await cache_set("products:featured", response, ex=120)
    return response


@router.get("")
async def list_products(
    search: str | None = None,
    category: str | None = None,
    categories: list[str] | None = Query(default=None),
    tag: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    in_stock: bool | None = None,
    min_rating: int | None = None,
    sort: str = "popular",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(
        Product.is_active == True,
        Product.is_group_parent == False,  # Exclude grouped child products from main listing
        Product.has_variants == False,  # Exclude variable products (show only parent)
    ).options(
        selectinload(Product.images),
        selectinload(Product.tiers),
        selectinload(Product.customizations),
        selectinload(Product.category),
    )

    if search:
        query = query.where(or_(
            Product.name.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%"),
        ))
    # Build category filter — supports multi-value ?categories= or legacy ?category=
    slugs = categories or ([category] if category else [])
    if slugs:
        query = query.join(Category).where(Category.slug.in_(slugs))
    if tag:
        query = query.where(Product.tags.contains([tag]))
    if min_price is not None:
        query = query.where(Product.base_price >= min_price)
    if max_price is not None:
        query = query.where(Product.base_price <= max_price)
    if in_stock:
        query = query.where(Product.stock > 0)
    if min_rating is not None:
        query = query.where(Product.rating >= min_rating)

    # Sorting
    if sort == "price_asc":
        query = query.order_by(Product.base_price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.base_price.desc())
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    elif sort == "rating":
        query = query.order_by(Product.rating.desc())
    else:  # popular
        query = query.order_by(Product.reviews_count.desc())

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Paginate
    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    products = result.scalars().all()

    return {
        "products": [_product_response(p) for p in products],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/ads")
async def get_public_ads(
    position: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint to fetch active ads with caching."""
    from app.redis import cache_get, cache_set
    from datetime import datetime, timezone

    cache_key = f"ads:{position or 'all'}"

    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    now = datetime.now(timezone.utc)

    query = select(Ad).where(Ad.is_active == True)
    if position:
        query = query.where(Ad.position == position)

    query = query.where(
        (Ad.start_date.is_(None)) | (Ad.start_date <= now)
    )
    query = query.where(
        (Ad.end_date.is_(None)) | (Ad.end_date >= now)
    )

    query = query.order_by(Ad.sort_order, Ad.created_at.desc())
    result = await db.execute(query)
    ads = result.scalars().all()

    response = [
        {
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "imageUrl": ad.image_url,
            "mobileImageUrl": ad.mobile_image_url,
            "linkUrl": ad.link_url,
            "position": ad.position,
        }
        for ad in ads
    ]

    await cache_set(cache_key, response, ex=300)
    return response


@router.get("/{slug}/related")
async def related_products(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get related products based on category and price similarity."""
    result = await db.execute(
        select(Product)
        .where(Product.slug == slug)
        .options(selectinload(Product.category))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Find products in same category with similar price (±30%)
    min_price = product.base_price * 0.7
    max_price = product.base_price * 1.3
    
    result = await db.execute(
        select(Product)
        .where(
            Product.is_active == True,
            Product.id != product.id,
            Product.category_id == product.category_id,
            Product.base_price >= min_price,
            Product.base_price <= max_price,
        )
        .options(
            selectinload(Product.images),
            selectinload(Product.tiers),
            selectinload(Product.customizations),
            selectinload(Product.category),
        )
        .order_by(Product.rating.desc())
        .limit(4)
    )
    
    related = result.scalars().all()
    return [_product_response(p) for p in related]


@router.get("/{slug}")
async def get_product(slug: str, db: AsyncSession = Depends(get_db)):
    """Get product by slug with caching."""
    from app.redis import cache_get, cache_set

    cached = await cache_get(f"product:{slug}")
    if cached is not None:
        return cached
    
    # If not cached, fetch from database
    result = await db.execute(
        select(Product)
        .where(Product.slug == slug, Product.is_active == True)
        .options(
            selectinload(Product.images),
            selectinload(Product.tiers),
            selectinload(Product.customizations),
            selectinload(Product.category),
            selectinload(Product.variants),
            selectinload(Product.product_group),
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    response = _product_response(product, include_category=True)
    
    # Add variants if variable product
    if product.has_variants:
        response["variants"] = [
            {
                "id": str(v.id),
                "sku": v.sku,
                "attributes": v.attributes,
                "price": v.price,
                "moq": v.moq,
                "stock": v.stock,
                "is_active": v.is_active,
            }
            for v in product.variants
            if v.is_active
        ]
    
    # Add grouped products if group parent
    if product.is_group_parent and product.product_group:
        result = await db.execute(
            select(Product)
            .where(
                Product.product_group_id == product.product_group.id,
                Product.is_active == True,
                Product.id != product.id,
            )
            .options(
                selectinload(Product.images),
                selectinload(Product.tiers),
                selectinload(Product.customizations),
            )
        )
        grouped_products = result.scalars().all()
        response["grouped_products"] = [_product_response(p) for p in grouped_products]
    
    await cache_set(f"product:{slug}", response, ex=300)
    return response


@router.get("/{product_id}/reviews")
async def list_reviews(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review).where(Review.product_id == product_id).order_by(Review.helpful_count.desc())
    )
    reviews = result.scalars().all()
    return [
        {
            "id": str(r.id), "author": r.author, "rating": r.rating,
            "title": r.title, "text": r.text, "date": r.created_at.isoformat(),
            "verified": r.is_verified, "helpful": r.helpful_count,
        }
        for r in reviews
    ]


@router.post("/{product_id}/reviews")
async def submit_review(
    product_id: uuid.UUID,
    body: ReviewCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user),
):
    from app.redis import check_rate_limit
    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:review:{client_ip}", 3, 300):
        raise HTTPException(status_code=429, detail="Too many reviews. Please wait.")

    review = Review(
        product_id=product_id,
        author=body.author,
        rating=body.rating,
        title=body.title,
        text=body.text,
    )
    db.add(review)
    await db.flush()
    
    # Invalidate product cache
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if product:
        await invalidate_product_cache(product.slug)
    
    return {"id": str(review.id), "message": "Review submitted"}


def _product_response(p: Product, include_category: bool = False) -> dict:
    resp = {
        "id": str(p.id),
        "slug": p.slug,
        "name": p.name,
        "category": p.category.slug if p.category is not None else None,
        "description": p.description,
        "basePrice": p.base_price,
        "moq": p.moq,
        "images": [img.url for img in p.images],
        "tiers": [{"qty": t.min_qty, "price": t.unit_price} for t in p.tiers],
        "customization": {
            "text": [{"label": c.label, "max": c.max_length} for c in p.customizations if c.type == "text"],
            "options": [{"label": c.label, "values": c.values} for c in p.customizations if c.type == "option"],
            "logoUpload": any(c.type == "logo" for c in p.customizations),
        },
        "customizationOptions": p.customization_options or {
            "colors": [],
            "allow_text": True,
            "allow_icon": True,
            "allow_image": True,
            "allowed_fonts": [],
            "default_text": "",
        },
        "stock": p.stock,
        "rating": p.rating,
        "reviews": p.reviews_count,
        "tags": p.tags or [],
    }
    return resp
