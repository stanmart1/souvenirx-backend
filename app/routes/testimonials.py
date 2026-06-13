from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database import get_db
from app.models.testimonial import Testimonial
from app.models.user import User
from app.middleware.auth import get_current_user, get_optional_user, get_current_admin

router = APIRouter()


@router.get("")
async def list_testimonials(
    featured_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List approved testimonials, optionally only featured ones."""
    query = select(Testimonial).where(Testimonial.is_approved == True)
    
    if featured_only:
        query = query.where(Testimonial.is_featured == True)
    
    result = await db.execute(query.order_by(Testimonial.created_at.desc()))
    testimonials = result.scalars().all()
    
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "role": t.role,
            "company": t.company,
            "text": t.text,
            "rating": t.rating,
            "media_url": t.media_url,
            "media_type": t.media_type,
            "date": t.created_at.isoformat(),
        }
        for t in testimonials
    ]


@router.post("")
async def create_testimonial(
    name: str,
    text: str,
    rating: int = 5,
    role: str | None = None,
    company: str | None = None,
    media: UploadFile | None = File(None),
    user: User = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a testimonial for approval."""
    import uuid
    
    # Handle media upload
    media_url = None
    media_type = None
    if media:
        allowed_types = ["image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"]
        if media.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        media_url = f"/uploads/testimonials/{media.filename}"
        media_type = "image" if media.content_type.startswith("image/") else "video"
    
    testimonial = Testimonial(
        user_id=user.id if user else None,
        name=name,
        role=role,
        company=company,
        text=text,
        rating=rating,
        media_url=media_url,
        media_type=media_type,
        is_approved=False,  # Requires admin approval
    )
    db.add(testimonial)
    await db.flush()
    
    return {
        "id": str(testimonial.id),
        "message": "Testimonial submitted for review",
    }


# --- Admin endpoints ---

@router.get("/admin/all")
async def admin_list_all_testimonials(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: List all testimonials (approved and pending)."""
    result = await db.execute(
        select(Testimonial).order_by(Testimonial.created_at.desc())
    )
    testimonials = result.scalars().all()
    
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "role": t.role,
            "company": t.company,
            "text": t.text,
            "rating": t.rating,
            "media_url": t.media_url,
            "media_type": t.media_type,
            "is_approved": t.is_approved,
            "is_featured": t.is_featured,
            "created_at": t.created_at.isoformat(),
        }
        for t in testimonials
    ]


@router.patch("/admin/{testimonial_id}/approve")
async def admin_approve_testimonial(
    testimonial_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Approve a testimonial."""
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == uuid.UUID(testimonial_id))
    )
    testimonial = result.scalar_one_or_none()
    
    if not testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    
    testimonial.is_approved = True
    await db.commit()
    
    return {"message": "Testimonial approved"}


@router.patch("/admin/{testimonial_id}/feature")
async def admin_feature_testimonial(
    testimonial_id: str,
    featured: bool,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Feature/unfeature a testimonial."""
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == uuid.UUID(testimonial_id))
    )
    testimonial = result.scalar_one_or_none()
    
    if not testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    
    testimonial.is_featured = featured
    await db.commit()
    
    return {"message": f"Testimonial {'featured' if featured else 'unfeatured'}"}


@router.delete("/admin/{testimonial_id}")
async def admin_delete_testimonial(
    testimonial_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Delete a testimonial."""
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == uuid.UUID(testimonial_id))
    )
    testimonial = result.scalar_one_or_none()
    
    if not testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    
    await db.delete(testimonial)
    await db.commit()
    
    return {"message": "Testimonial deleted"}
