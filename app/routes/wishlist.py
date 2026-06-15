import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.models.product import Product
from app.schemas.wishlist import WishlistItemAdd, WishlistItemResponse

router = APIRouter()


@router.get("")
async def get_wishlist(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all items in the user's wishlist."""
    result = await db.execute(
        select(WishlistItem)
        .where(WishlistItem.user_id == user.id)
        .options(selectinload(WishlistItem.product))
        .order_by(WishlistItem.created_at.desc())
    )
    items = result.scalars().all()
    return [_wishlist_item_response(item) for item in items]


@router.post("")
async def add_to_wishlist(
    body: WishlistItemAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a product to the wishlist."""
    # Check product exists
    result = await db.execute(select(Product).where(Product.id == body.product_id, Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if already in wishlist
    result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.user_id == user.id, 
            WishlistItem.product_id == body.product_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return {"message": "Product already in wishlist", "id": existing.id}

    # Add to wishlist
    item = WishlistItem(
        user_id=user.id, 
        product_id=body.product_id
    )
    db.add(item)
    await db.flush()
    
    return {"message": "Product added to wishlist", "id": item.id}


@router.delete("/{product_id}")
async def remove_from_wishlist(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a product from the wishlist."""
    result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.user_id == user.id,
            WishlistItem.product_id == product_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Product not in wishlist")

    await db.delete(item)
    await db.flush()
    return {"message": "Product removed from wishlist"}


@router.delete("")
async def clear_wishlist(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Clear all items from the wishlist."""
    result = await db.execute(select(WishlistItem).where(WishlistItem.user_id == user.id))
    items = result.scalars().all()
    for item in items:
        await db.delete(item)
    await db.flush()
    return {"message": "Wishlist cleared"}


@router.get("/check/{product_id}")
async def check_wishlist(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a product is in the user's wishlist."""
    result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.user_id == user.id,
            WishlistItem.product_id == product_id
        )
    )
    item = result.scalar_one_or_none()
    return {"in_wishlist": item is not None}


def _wishlist_item_response(item: WishlistItem) -> dict:
    """Format wishlist item response."""
    product = item.product
    
    return {
        "id": item.id,
        "productId": str(item.product_id),
        "productName": product.name,
        "productSlug": product.slug,
        "productPrice": product.base_price,
        "productImage": product.images[0] if product.images else None,
        "productStock": product.stock,
        "createdAt": item.created_at.isoformat(),
    }
