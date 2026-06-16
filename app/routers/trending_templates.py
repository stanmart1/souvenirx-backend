"""
Trending Templates API Endpoints
Manages trending/featured templates for home screen
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
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


# Public endpoints
@router.get("/", response_model=List[TrendingTemplateResponse])
async def get_trending_templates(
    limit: int = Query(10, ge=1, le=50),
    featured_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get trending templates for home screen"""
    now = datetime.now(timezone.utc)
    
    query = db.query(TrendingTemplate).filter(
        TrendingTemplate.is_active == True
    )
    
    if featured_only:
        query = query.filter(
            and_(
                TrendingTemplate.is_featured == True,
                (TrendingTemplate.featured_from == None) | (TrendingTemplate.featured_from <= now),
                (TrendingTemplate.featured_until == None) | (TrendingTemplate.featured_until >= now)
            )
        )
    
    templates = query.order_by(
        desc(TrendingTemplate.display_order),
        desc(TrendingTemplate.trending_score)
    ).limit(limit).all()
    
    return [template.to_dict() for template in templates]


@router.get("/{trending_id}", response_model=TrendingTemplateResponse)
async def get_trending_template(
    trending_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific trending template"""
    template = db.query(TrendingTemplate).filter(
        TrendingTemplate.id == uuid.UUID(trending_id)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")
    
    return template.to_dict()


@router.post("/{trending_id}/track-view")
async def track_template_view(
    trending_id: str,
    db: Session = Depends(get_db)
):
    """Track a view for trending calculation"""
    template = db.query(TrendingTemplate).filter(
        TrendingTemplate.id == uuid.UUID(trending_id)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")
    
    template.view_count_24h += 1
    
    # Recalculate trending score
    # Simple algorithm: (views_24h * 0.3) + (usage_7d * 0.7)
    template.trending_score = (template.view_count_24h * 0.3) + (template.usage_count_7d * 0.7)
    
    db.commit()
    
    return {"message": "View tracked"}


@router.post("/{trending_id}/track-usage")
async def track_template_usage(
    trending_id: str,
    db: Session = Depends(get_db)
):
    """Track a usage for trending calculation"""
    template = db.query(TrendingTemplate).filter(
        TrendingTemplate.id == uuid.UUID(trending_id)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")
    
    template.usage_count_7d += 1
    
    # Recalculate trending score
    template.trending_score = (template.view_count_24h * 0.3) + (template.usage_count_7d * 0.7)
    
    db.commit()
    
    return {"message": "Usage tracked"}


# Admin endpoints
@router.post("/", response_model=TrendingTemplateResponse, dependencies=[Depends(require_admin)])
async def create_trending_template(
    template_data: TrendingTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a template to trending (Admin only)"""
    # Check if template exists
    design_template = db.query(DesignTemplate).filter(
        DesignTemplate.id == uuid.UUID(template_data.template_id)
    ).first()
    
    if not design_template:
        raise HTTPException(status_code=404, detail="Design template not found")
    
    # Check if already in trending
    existing = db.query(TrendingTemplate).filter(
        TrendingTemplate.template_id == uuid.UUID(template_data.template_id)
    ).first()
    
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
    db.commit()
    db.refresh(trending)
    
    return trending.to_dict()


@router.put("/{trending_id}", response_model=TrendingTemplateResponse, dependencies=[Depends(require_admin)])
async def update_trending_template(
    trending_id: str,
    template_data: TrendingTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a trending template (Admin only)"""
    template = db.query(TrendingTemplate).filter(
        TrendingTemplate.id == uuid.UUID(trending_id)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")
    
    # Update fields
    update_data = template_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)
    
    db.commit()
    db.refresh(template)
    
    return template.to_dict()


@router.delete("/{trending_id}", dependencies=[Depends(require_admin)])
async def delete_trending_template(
    trending_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a template from trending (Admin only)"""
    template = db.query(TrendingTemplate).filter(
        TrendingTemplate.id == uuid.UUID(trending_id)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Trending template not found")
    
    db.delete(template)
    db.commit()
    
    return {"message": "Trending template removed"}


@router.post("/reset-metrics", dependencies=[Depends(require_admin)])
async def reset_trending_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reset 24h and 7d metrics (Admin only - run daily)"""
    # Reset 24h views
    db.query(TrendingTemplate).update({
        TrendingTemplate.view_count_24h: 0
    })
    
    # Decay 7d usage (reduce by 1/7 each day)
    templates = db.query(TrendingTemplate).all()
    for template in templates:
        template.usage_count_7d = int(template.usage_count_7d * 6 / 7)
        template.trending_score = (template.view_count_24h * 0.3) + (template.usage_count_7d * 0.7)
    
    db.commit()
    
    return {"message": "Metrics reset successfully"}


@router.get("/admin/all", response_model=List[TrendingTemplateResponse], dependencies=[Depends(require_admin)])
async def get_all_trending_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all trending templates (Admin only)"""
    templates = db.query(TrendingTemplate).order_by(
        desc(TrendingTemplate.trending_score)
    ).offset(skip).limit(limit).all()
    
    return [template.to_dict() for template in templates]


@router.get("/admin/stats", dependencies=[Depends(require_admin)])
async def get_trending_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trending templates statistics (Admin only)"""
    total = db.query(TrendingTemplate).count()
    active = db.query(TrendingTemplate).filter(TrendingTemplate.is_active == True).count()
    featured = db.query(TrendingTemplate).filter(TrendingTemplate.is_featured == True).count()
    
    # Get top trending
    top = db.query(TrendingTemplate).order_by(
        desc(TrendingTemplate.trending_score)
    ).limit(5).all()
    
    return {
        'total': total,
        'active': active,
        'featured': featured,
        'top_trending': [t.to_dict() for t in top]
    }
