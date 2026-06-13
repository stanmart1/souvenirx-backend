import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.cart import CartItem
from app.models.product import Product, ProductTier, ProductVariant
from app.schemas.cart import CartItemAdd, CartItemUpdate

router = APIRouter()


@router.get("")
async def get_cart(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CartItem)
        .where(CartItem.user_id == user.id)
        .options(
            selectinload(CartItem.product).selectinload(Product.tiers),
            selectinload(CartItem.variant)
        )
    )
    items = result.scalars().all()
    return [_cart_item_response(item) for item in items]


@router.post("")
async def add_to_cart(
    body: CartItemAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check product exists
    result = await db.execute(select(Product).where(Product.id == body.product_id, Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check variant exists if provided
    if body.variant_id:
        result = await db.execute(select(ProductVariant).where(ProductVariant.id == body.variant_id, ProductVariant.product_id == body.product_id, ProductVariant.is_active == True))
        variant = result.scalar_one_or_none()
        if not variant:
            raise HTTPException(status_code=404, detail="Variant not found")

    # Check if already in cart (same product + variant combination)
    result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == user.id, 
            CartItem.product_id == body.product_id,
            (CartItem.variant_id == body.variant_id) if body.variant_id else CartItem.variant_id.is_(None)
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.qty += body.qty
        if body.customization:
            existing.customization = body.customization
        if body.logo_url:
            existing.logo_url = body.logo_url
    else:
        item = CartItem(
            user_id=user.id, 
            product_id=body.product_id, 
            variant_id=body.variant_id,
            qty=body.qty, 
            customization=body.customization,
            logo_url=body.logo_url
        )
        db.add(item)

    await db.flush()
    return {"message": "Item added to cart"}


@router.put("/{item_id}")
async def update_cart_item(
    item_id: int,
    body: CartItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if body.qty is not None:
        item.qty = max(1, body.qty)
    if body.customization is not None:
        item.customization = body.customization
    if body.logo_url is not None:
        item.logo_url = body.logo_url

    await db.flush()
    return {"message": "Cart item updated"}


@router.delete("/{item_id}")
async def remove_cart_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await db.delete(item)
    await db.flush()
    return {"message": "Item removed"}


@router.delete("")
async def clear_cart(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CartItem).where(CartItem.user_id == user.id))
    items = result.scalars().all()
    for item in items:
        await db.delete(item)
    await db.flush()
    return {"message": "Cart cleared"}


def _cart_item_response(item: CartItem) -> dict:
    product = item.product
    variant = item.variant
    
    # Use variant price if variant is selected, otherwise use base price
    base_price = variant.price if variant else product.base_price
    
    # Find best tier price
    unit_price = base_price
    for tier in sorted(product.tiers, key=lambda t: t.min_qty):
        if item.qty >= tier.min_qty:
            unit_price = tier.unit_price

    return {
        "id": item.id,
        "productId": str(item.product_id),
        "productName": product.name,
        "qty": item.qty,
        "unitPrice": unit_price,
        "customization": item.customization,
        "variantId": str(item.variant_id) if item.variant_id else None,
        "variantAttributes": variant.attributes if variant else None,
        "logoUrl": item.logo_url,
    }
