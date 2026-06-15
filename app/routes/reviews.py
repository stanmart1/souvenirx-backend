from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.review import Review
from app.models.product import Product
from app.models.user import User
from app.middleware.auth import get_current_user, get_optional_user, get_current_admin
from app.redis import check_rate_limit
from app.schemas.product import ReviewCreate

router = APIRouter()


@router.post("/{product_id}")
async def create_review(
    product_id: str,
    author: str,
    rating: int,
    title: str,
    text: str,
    media: UploadFile | None = File(None),
    user: User = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new review with optional media upload."""
    import uuid
    
    # Check if product exists
    result = await db.execute(select(Product).where(Product.id == uuid.UUID(product_id)))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Handle media upload
    media_url = None
    media_type = None
    if media:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"]
        if media.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # In production, upload to cloud storage
        # For now, just store the filename
        media_url = f"/uploads/reviews/{media.filename}"
        media_type = "image" if media.content_type.startswith("image/") else "video"
    
    review = Review(
        product_id=uuid.UUID(product_id),
        user_id=user.id if user else None,
        author=author,
        rating=rating,
        title=title,
        text=text,
        media_url=media_url,
        media_type=media_type,
        is_verified=bool(user),  # Verified if logged in user
    )
    db.add(review)
    await db.flush()
    
    # Update product rating
    all_reviews = await db.execute(
        select(Review).where(Review.product_id == uuid.UUID(product_id))
    )
    reviews = all_reviews.scalars().all()
    avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
    product.rating = round(avg_rating, 1)
    product.reviews_count = len(reviews)
    
    return {
        "id": str(review.id),
        "message": "Review created successfully",
    }


@router.get("/{product_id}")
async def list_reviews(
    product_id: str,
    media_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List reviews for a product, optionally filtered by media type."""
    import uuid
    
    query = select(Review).where(Review.product_id == uuid.UUID(product_id))
    
    if media_type:
        query = query.where(Review.media_type == media_type)
    
    result = await db.execute(query.order_by(Review.helpful_count.desc()))
    reviews = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "author": r.author,
            "rating": r.rating,
            "title": r.title,
            "text": r.text,
            "media_url": r.media_url,
            "media_type": r.media_type,
            "is_verified": r.is_verified,
            "helpful": r.helpful_count,
            "date": r.created_at.isoformat(),
        }
        for r in reviews
    ]


@router.post("/{review_id}/helpful")
async def mark_helpful(review_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    import uuid

    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:helpful:{client_ip}:{review_id}", 1, 60):
        raise HTTPException(status_code=429, detail="Please wait before voting again.")

    result = await db.execute(select(Review).where(Review.id == uuid.UUID(review_id)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.helpful_count += 1
    await db.flush()
    return {"helpful": review.helpful_count}


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@router.patch("/admin/{review_id}/approve")
async def admin_approve_review(
    review_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Approve a review."""
    import uuid
    result = await db.execute(select(Review).where(Review.id == uuid.UUID(review_id)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_approved = True
    await db.flush()
    return {"message": "Review approved"}


@router.patch("/admin/{review_id}/reject")
async def admin_reject_review(
    review_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Reject (unapprove) a review."""
    import uuid
    result = await db.execute(select(Review).where(Review.id == uuid.UUID(review_id)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_approved = False
    await db.flush()
    return {"message": "Review rejected"}


@router.patch("/admin/{review_id}/feature")
async def admin_feature_review(
    review_id: str,
    featured: bool,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Feature/unfeature a review."""
    import uuid
    result = await db.execute(select(Review).where(Review.id == uuid.UUID(review_id)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_featured = featured
    await db.flush()
    return {"message": f"Review {'featured' if featured else 'unfeatured'}"}


@router.post("/admin/{review_id}/reply")
async def admin_reply_to_review(
    review_id: str,
    reply: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Add or update reply to a review."""
    import uuid
    from datetime import datetime, timezone
    
    result = await db.execute(select(Review).where(Review.id == uuid.UUID(review_id)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.admin_reply = reply
    review.admin_reply_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Reply added"}


@router.delete("/admin/{review_id}/reply")
async def admin_delete_reply(
    review_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Delete reply from a review."""
    import uuid
    
    result = await db.execute(select(Review).where(Review.id == uuid.UUID(review_id)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.admin_reply = None
    review.admin_reply_at = None
    await db.flush()
    return {"message": "Reply deleted"}
