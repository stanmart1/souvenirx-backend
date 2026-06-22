"""
Trending Templates API Endpoints
Manages trending/featured templates for home screen
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, and_, select, func, update
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from app.database import get_db
from app.models.trending_template import TrendingTemplate
from app.models.design_template import DesignTemplate
from app.models.user import User
from app.dependencies import get_current_user, require_admin
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/trending-templates", tags=["Trending Templates"])


# Pydantic schemas
class TrendingTemplateCreate(BaseModel):
    template_id: str
    display_name: Optional[str] = None
    display_order: int = 0
    is_featured: bool = False
    featured_from: Optional[datetime] = None
    featured_until: Optional[datetime] = None


class TrendingTemplateUpdate(BaseModel):
    display_name: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    featured_from: Optional[datetime] = None
    featured_until: Optional[datetime] = None


class TrendingTemplateResponse(BaseModel):
    id: str
    template_id: str
    display_name: Optional[str]
    display_order: int
    trending_score: float
    view_count_24h: int
    usage_count_7d: int
    is_active: bool
    is_featured: bool
    featured_from: Optional[str]
    featured_until: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    template: Optional[dict] = None

    class Config:
        from_attributes = True


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.get("/", response_model=List[TrendingTemplateResponse])
async def get_trending_templates(
    limit: int = Query(10, ge=1, le=50),
    featured_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get trending templates for home screen"""
    now = datetime.now(timezone.utc)

    stmt = select(TrendingTemplate).options(
        selectinload(TrendingTemplate.template)
    ).where(TrendingTemplate.is_active == True)

    if featured_only:
        stmt = stmt.where(
            and_(
                TrendingTemplate.is_featured == True,
                (TrendingTemplate.featured_from == None) | (TrendingTemplate.featured_from <= now),
                (TrendingTemplate.featured_until == None) | (TrendingTemplate.featured_until >= now)
            )
        )

    stmt = stmt.order_by(
        desc(TrendingTemplate.display_order),
        desc(TrendingTemplate.trending_score)
    ).limit(limit)

    templates = (await db.execute(stmt)).scalars().all()

    return [template.to_dict() for template in templates]


# ── Admin GET endpoints — defined BEFORE /{trending_id} to prevent shadowing ──

@router.get("/admin/all", response_model=List[TrendingTemplateResponse], dependencies=[Depends(require_admin)])
async def get_all_trending_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all trending templates (Admin only)"""
    templates = (await db.execute(
        select(TrendingTemplate).options(
            selectinload(TrendingTemplate.template)
        ).order_by(
            desc(TrendingTemplate.trending_score)
        ).offset(skip).limit(limit)
    )).scalars().all()

    return [template.to_dict() for template in templates]


@router.get("/admin/stats", dependencies=[Depends(require_admin)])
async def get_trending_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trending templates statistics (Admin only)"""
    total = (await db.execute(
        select(func.count()).select_from(TrendingTemplate)
    )).scalar()

    active = (await db.execute(
        select(func.count()).select_from(TrendingTemplate).where(TrendingTemplate.is_active == True)
    )).scalar()

    featured = (await db.execute(
        select(func.count()).select_from(TrendingTemplate).where(TrendingTemplate.is_featured == True)
    )).scalar()

    # Get top trending
    top = (await db.execute(
        select(TrendingTemplate).options(
            selectinload(TrendingTemplate.template)
        ).order_by(
            desc(TrendingTemplate.trending_score)
        ).limit(5)
    )).scalars().all()

    return {
        'total': total,
        'active': active,
        'featured': featured,
        'top_trending': [t.to_dict() for t in top]
    }


# ── Parameterised GET — after all static GET paths ───────────────────────────

@router.get("/{trending_id}", response_model=TrendingTemplateResponse)
async def get_trending_template(
    trending_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific trending template"""
    try:
        trending_uuid = uuid.UUID(trending_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format for trending_id")

    template = (await db.execute(
        select(TrendingTemplate).options(
            selectinload(TrendingTemplate.template)
        ).where(TrendingTemplate.id == trending_uuid)
    )).scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")

    return template.to_dict()


# ── POST /reset-metrics — defined BEFORE POST / to avoid route conflicts ─────

@router.post("/reset-metrics", dependencies=[Depends(require_admin)])
async def reset_trending_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reset 24h and 7d metrics (Admin only - run daily)"""
    # Reset 24h views
    await db.execute(update(TrendingTemplate).values(view_count_24h=0))

    # Decay 7d usage (reduce by 1/7 each day)
    templates = (await db.execute(select(TrendingTemplate))).scalars().all()
    for template in templates:
        template.usage_count_7d = int(template.usage_count_7d * 6 / 7)
        template.trending_score = (template.view_count_24h * 0.3) + (template.usage_count_7d * 0.7)

    await db.commit()

    return {"message": "Metrics reset successfully"}


@router.post("/", response_model=TrendingTemplateResponse, dependencies=[Depends(require_admin)])
async def create_trending_template(
    template_data: TrendingTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a template to trending (Admin only)"""
    try:
        template_uuid = uuid.UUID(template_data.template_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format for template_id")

    # Check if template exists
    design_template = (await db.execute(
        select(DesignTemplate).where(DesignTemplate.id == template_uuid)
    )).scalar_one_or_none()

    if not design_template:
        raise HTTPException(status_code=404, detail="Design template not found")

    # Check if already in trending
    existing = (await db.execute(
        select(TrendingTemplate).where(TrendingTemplate.template_id == template_uuid)
    )).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Template already in trending")

    # Create trending template
    trending = TrendingTemplate(
        **template_data.dict(),
        is_active=True,
        trending_score=0.0,
        view_count_24h=0,
        usage_count_7d=0
    )

    db.add(trending)
    await db.commit()
    await db.refresh(trending)

    # Eager-load the template relationship to avoid lazy-load in async context
    trending = (await db.execute(
        select(TrendingTemplate).options(
            selectinload(TrendingTemplate.template)
        ).where(TrendingTemplate.id == trending.id)
    )).scalar_one()

    return trending.to_dict()


# ── Parameterised POST endpoints ──────────────────────────────────────────────

@router.post("/{trending_id}/track-view")
async def track_template_view(
    trending_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Track a view for trending calculation"""
    try:
        trending_uuid = uuid.UUID(trending_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format for trending_id")

    template = (await db.execute(
        select(TrendingTemplate).where(TrendingTemplate.id == trending_uuid)
    )).scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")

    template.view_count_24h += 1

    # Recalculate trending score
    # Simple algorithm: (views_24h * 0.3) + (usage_7d * 0.7)
    template.trending_score = (template.view_count_24h * 0.3) + (template.usage_count_7d * 0.7)

    await db.commit()

    return {"message": "View tracked"}


@router.post("/{trending_id}/track-usage")
async def track_template_usage(
    trending_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Track a usage for trending calculation"""
    try:
        trending_uuid = uuid.UUID(trending_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format for trending_id")

    template = (await db.execute(
        select(TrendingTemplate).where(TrendingTemplate.id == trending_uuid)
    )).scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")

    template.usage_count_7d += 1

    # Recalculate trending score
    template.trending_score = (template.view_count_24h * 0.3) + (template.usage_count_7d * 0.7)

    await db.commit()

    return {"message": "Usage tracked"}


# ── Admin PUT / DELETE ────────────────────────────────────────────────────────

@router.put("/{trending_id}", response_model=TrendingTemplateResponse, dependencies=[Depends(require_admin)])
async def update_trending_template(
    trending_id: str,
    template_data: TrendingTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a trending template (Admin only)"""
    try:
        trending_uuid = uuid.UUID(trending_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format for trending_id")

    template = (await db.execute(
        select(TrendingTemplate).options(
            selectinload(TrendingTemplate.template)
        ).where(TrendingTemplate.id == trending_uuid)
    )).scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")

    # Update fields
    update_data = template_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.commit()

    # Re-query with eager-loaded template to avoid lazy-load in async context
    template = (await db.execute(
        select(TrendingTemplate).options(
            selectinload(TrendingTemplate.template)
        ).where(TrendingTemplate.id == trending_uuid)
    )).scalar_one()

    return template.to_dict()


@router.delete("/{trending_id}", dependencies=[Depends(require_admin)])
async def delete_trending_template(
    trending_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a template from trending (Admin only)"""
    try:
        trending_uuid = uuid.UUID(trending_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format for trending_id")

    template = (await db.execute(
        select(TrendingTemplate).where(TrendingTemplate.id == trending_uuid)
    )).scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")

    db.delete(template)
    await db.commit()

    return {"message": "Trending template removed"}
