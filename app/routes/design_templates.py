"""Design template management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import selectinload
from typing import Optional
import uuid

from app.database import get_db
from app.middleware.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.design_template import DesignTemplate, CustomerDesign
from app.models.product import Product
from app.services.audit import log_admin_action

router = APIRouter(prefix="/api/design-templates", tags=["design-templates"])


# ============================================================================
# ADMIN ENDPOINTS - Template Management
# ============================================================================

@router.get("/admin/templates")
async def list_design_templates_admin(
    category: Optional[str] = None,
    style: Optional[str] = None,
    is_featured: Optional[bool] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List all design templates (admin view).
    
    Supports filtering by:
    - category: Template category
    - style: Template style
    - is_featured: Featured templates
    - is_active: Active/inactive templates
    - search: Search in name and description
    """
    query = select(DesignTemplate).options(
        selectinload(DesignTemplate.creator)
    )
    
    # Apply filters
    if category:
        query = query.where(DesignTemplate.category == category)
    if style:
        query = query.where(DesignTemplate.style == style)
    if is_featured is not None:
        query = query.where(DesignTemplate.is_featured == is_featured)
    if is_active is not None:
        query = query.where(DesignTemplate.is_active == is_active)
    if search:
        query = query.where(
            or_(
                DesignTemplate.name.ilike(f"%{search}%"),
                DesignTemplate.description.ilike(f"%{search}%")
            )
        )
    
    # Order by popularity and featured status
    query = query.order_by(
        DesignTemplate.is_featured.desc(),
        DesignTemplate.popularity_score.desc(),
        DesignTemplate.created_at.desc()
    )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        query.offset((page - 1) * limit).limit(limit)
    )
    templates = result.scalars().all()
    
    return {
        "templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "slug": t.slug,
                "description": t.description,
                "category": t.category,
                "style": t.style,
                "tags": t.tags or [],
                "thumbnail": t.thumbnail_url,
                "preview_images": t.preview_images or [],
                "compatible_products": t.compatible_products or [],
                "is_premium": t.is_premium,
                "premium_price": t.premium_price,
                "usage_count": t.usage_count,
                "popularity_score": t.popularity_score,
                "is_featured": t.is_featured,
                "is_active": t.is_active,
                "created_by": {
                    "id": str(t.creator.id),
                    "name": t.creator.name,
                    "email": t.creator.email,
                } if t.creator else None,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in templates
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    }


@router.post("/admin/templates")
async def create_design_template(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new design template.
    
    Required fields:
    - name: Template name
    - slug: URL-friendly slug
    - category: Template category
    - style: Template style
    - design_data: Complete design specification (JSONB)
    - thumbnail_url: Thumbnail image URL
    
    Optional fields:
    - description: Template description
    - tags: List of tags
    - preview_images: List of preview image URLs
    - compatible_products: List of product IDs or category slugs
    - is_premium: Premium template flag
    - premium_price: Extra charge in kobo
    - is_featured: Featured template flag
    """
    # Validate required fields
    required_fields = ['name', 'slug', 'category', 'style', 'design_data', 'thumbnail_url']
    for field in required_fields:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Check if slug already exists
    result = await db.execute(
        select(DesignTemplate).where(DesignTemplate.slug == body['slug'])
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")
    
    # Validate design_data structure
    design_data = body['design_data']
    if not isinstance(design_data, dict):
        raise HTTPException(status_code=400, detail="design_data must be a JSON object")
    
    if 'layers' not in design_data:
        raise HTTPException(status_code=400, detail="design_data must contain 'layers' array")
    
    # Create template
    template = DesignTemplate(
        name=body['name'],
        slug=body['slug'],
        description=body.get('description'),
        category=body['category'],
        style=body['style'],
        tags=body.get('tags', []),
        design_data=design_data,
        thumbnail_url=body['thumbnail_url'],
        preview_images=body.get('preview_images', []),
        compatible_products=body.get('compatible_products', []),
        is_premium=body.get('is_premium', False),
        premium_price=body.get('premium_price', 0),
        is_featured=body.get('is_featured', False),
        created_by=admin.id,
    )
    
    db.add(template)
    await db.commit()
    await db.refresh(template)
    
    # Log admin action
    await log_admin_action(
        db=db,
        admin_id=admin.id,
        action="create_design_template",
        resource_type="design_template",
        resource_id=str(template.id),
        details={"name": template.name, "category": template.category}
    )
    
    return {
        "id": str(template.id),
        "message": "Template created successfully",
        "template": {
            "id": str(template.id),
            "name": template.name,
            "slug": template.slug,
            "category": template.category,
        }
    }


@router.get("/admin/templates/{template_id}")
async def get_template_detail_admin(
    template_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get full template details including design data (admin view)"""
    result = await db.execute(
        select(DesignTemplate)
        .options(selectinload(DesignTemplate.creator))
        .where(DesignTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": str(template.id),
        "name": template.name,
        "slug": template.slug,
        "description": template.description,
        "category": template.category,
        "style": template.style,
        "tags": template.tags or [],
        "design_data": template.design_data,
        "thumbnail": template.thumbnail_url,
        "preview_images": template.preview_images or [],
        "compatible_products": template.compatible_products or [],
        "is_premium": template.is_premium,
        "premium_price": template.premium_price,
        "usage_count": template.usage_count,
        "popularity_score": template.popularity_score,
        "is_featured": template.is_featured,
        "is_active": template.is_active,
        "created_by": {
            "id": str(template.creator.id),
            "name": template.creator.name,
            "email": template.creator.email,
        } if template.creator else None,
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


@router.put("/admin/templates/{template_id}")
async def update_design_template(
    template_id: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a design template.
    
    All fields are optional. Only provided fields will be updated.
    """
    result = await db.execute(
        select(DesignTemplate).where(DesignTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Track changes for audit log
    changes = {}
    
    # Update fields
    updatable_fields = [
        'name', 'slug', 'description', 'category', 'style', 'tags',
        'design_data', 'thumbnail_url', 'preview_images', 'compatible_products',
        'is_premium', 'premium_price', 'is_featured', 'is_active', 'popularity_score'
    ]
    
    for field in updatable_fields:
        if field in body:
            old_value = getattr(template, field)
            new_value = body[field]
            
            if old_value != new_value:
                changes[field] = {"old": old_value, "new": new_value}
                setattr(template, field, new_value)
    
    # Validate slug uniqueness if changed
    if 'slug' in body and body['slug'] != template.slug:
        result = await db.execute(
            select(DesignTemplate).where(
                DesignTemplate.slug == body['slug'],
                DesignTemplate.id != template_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already exists")
    
    await db.commit()
    
    # Log admin action
    if changes:
        await log_admin_action(
            db=db,
            admin_id=admin.id,
            action="update_design_template",
            resource_type="design_template",
            resource_id=str(template.id),
            details={"changes": changes}
        )
    
    return {
        "message": "Template updated successfully",
        "changes": list(changes.keys())
    }


@router.delete("/admin/templates/{template_id}")
async def delete_design_template(
    template_id: str,
    hard_delete: bool = Query(False, description="Permanently delete (true) or soft delete (false)"),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a design template.
    
    - hard_delete=false: Soft delete (set is_active=false)
    - hard_delete=true: Permanently delete from database
    """
    result = await db.execute(
        select(DesignTemplate).where(DesignTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if hard_delete:
        # Check if template is being used
        result = await db.execute(
            select(func.count())
            .select_from(CustomerDesign)
            .where(CustomerDesign.template_id == template_id)
        )
        usage_count = result.scalar()
        
        if usage_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete template. It is being used by {usage_count} customer designs. Use soft delete instead."
            )
        
        # Hard delete
        await db.delete(template)
        action = "hard_delete_design_template"
        message = "Template permanently deleted"
    else:
        # Soft delete
        template.is_active = False
        action = "soft_delete_design_template"
        message = "Template deactivated"
    
    await db.commit()
    
    # Log admin action
    await log_admin_action(
        db=db,
        admin_id=admin.id,
        action=action,
        resource_type="design_template",
        resource_id=str(template.id),
        details={"name": template.name, "hard_delete": hard_delete}
    )
    
    return {"message": message}


@router.post("/admin/templates/{template_id}/duplicate")
async def duplicate_design_template(
    template_id: str,
    new_name: Optional[str] = None,
    new_slug: Optional[str] = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Duplicate an existing template.
    
    Creates a copy of the template with a new name and slug.
    """
    result = await db.execute(
        select(DesignTemplate).where(DesignTemplate.id == template_id)
    )
    original = result.scalar_one_or_none()
    
    if not original:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Generate new name and slug
    if not new_name:
        new_name = f"{original.name} (Copy)"
    if not new_slug:
        new_slug = f"{original.slug}-copy-{uuid.uuid4().hex[:8]}"
    
    # Check slug uniqueness
    result = await db.execute(
        select(DesignTemplate).where(DesignTemplate.slug == new_slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")
    
    # Create duplicate
    duplicate = DesignTemplate(
        name=new_name,
        slug=new_slug,
        description=original.description,
        category=original.category,
        style=original.style,
        tags=original.tags,
        design_data=original.design_data,
        thumbnail_url=original.thumbnail_url,
        preview_images=original.preview_images,
        compatible_products=original.compatible_products,
        is_premium=original.is_premium,
        premium_price=original.premium_price,
        is_featured=False,  # Don't copy featured status
        created_by=admin.id,
    )
    
    db.add(duplicate)
    await db.commit()
    await db.refresh(duplicate)
    
    # Log admin action
    await log_admin_action(
        db=db,
        admin_id=admin.id,
        action="duplicate_design_template",
        resource_type="design_template",
        resource_id=str(duplicate.id),
        details={
            "original_id": str(original.id),
            "original_name": original.name,
            "new_name": new_name
        }
    )
    
    return {
        "id": str(duplicate.id),
        "message": "Template duplicated successfully",
        "template": {
            "id": str(duplicate.id),
            "name": duplicate.name,
            "slug": duplicate.slug,
        }
    }


@router.get("/admin/templates/stats/overview")
async def get_templates_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get template statistics overview"""
    
    # Total templates
    result = await db.execute(select(func.count()).select_from(DesignTemplate))
    total_templates = result.scalar()
    
    # Active templates
    result = await db.execute(
        select(func.count())
        .select_from(DesignTemplate)
        .where(DesignTemplate.is_active == True)
    )
    active_templates = result.scalar()
    
    # Featured templates
    result = await db.execute(
        select(func.count())
        .select_from(DesignTemplate)
        .where(DesignTemplate.is_featured == True)
    )
    featured_templates = result.scalar()
    
    # Premium templates
    result = await db.execute(
        select(func.count())
        .select_from(DesignTemplate)
        .where(DesignTemplate.is_premium == True)
    )
    premium_templates = result.scalar()
    
    # Total usage
    result = await db.execute(
        select(func.sum(DesignTemplate.usage_count))
        .select_from(DesignTemplate)
    )
    total_usage = result.scalar() or 0
    
    # Templates by category
    result = await db.execute(
        select(
            DesignTemplate.category,
            func.count().label('count')
        )
        .group_by(DesignTemplate.category)
        .order_by(func.count().desc())
    )
    by_category = [{"category": row[0], "count": row[1]} for row in result.all()]
    
    # Most popular templates
    result = await db.execute(
        select(DesignTemplate)
        .where(DesignTemplate.is_active == True)
        .order_by(DesignTemplate.usage_count.desc())
        .limit(10)
    )
    popular_templates = result.scalars().all()
    
    return {
        "overview": {
            "total_templates": total_templates,
            "active_templates": active_templates,
            "featured_templates": featured_templates,
            "premium_templates": premium_templates,
            "total_usage": total_usage,
        },
        "by_category": by_category,
        "most_popular": [
            {
                "id": str(t.id),
                "name": t.name,
                "category": t.category,
                "usage_count": t.usage_count,
                "thumbnail": t.thumbnail_url,
            }
            for t in popular_templates
        ]
    }


# ============================================================================
# CUSTOMER ENDPOINTS - Template Discovery
# ============================================================================

@router.get("/categories")
async def get_template_categories(
    db: AsyncSession = Depends(get_db),
):
    """Get all available template categories with counts"""
    result = await db.execute(
        select(
            DesignTemplate.category,
            func.count().label('count')
        )
        .where(DesignTemplate.is_active == True)
        .group_by(DesignTemplate.category)
        .order_by(DesignTemplate.category)
    )
    
    categories = [
        {"category": row[0], "count": row[1]}
        for row in result.all()
    ]
    
    return {"categories": categories}


@router.get("/templates")
async def list_design_templates_customer(
    category: Optional[str] = None,
    style: Optional[str] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    List design templates for customers.
    
    Only returns active templates.
    """
    query = select(DesignTemplate).where(DesignTemplate.is_active == True)
    
    # Apply filters
    if category:
        query = query.where(DesignTemplate.category == category)
    if style:
        query = query.where(DesignTemplate.style == style)
    if is_featured is not None:
        query = query.where(DesignTemplate.is_featured == is_featured)
    if search:
        query = query.where(
            or_(
                DesignTemplate.name.ilike(f"%{search}%"),
                DesignTemplate.description.ilike(f"%{search}%")
            )
        )
    
    # Order by featured and popularity
    query = query.order_by(
        DesignTemplate.is_featured.desc(),
        DesignTemplate.popularity_score.desc()
    )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        query.offset((page - 1) * limit).limit(limit)
    )
    templates = result.scalars().all()
    
    return {
        "templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "slug": t.slug,
                "description": t.description,
                "category": t.category,
                "style": t.style,
                "tags": t.tags or [],
                "thumbnail": t.thumbnail_url,
                "preview_images": t.preview_images or [],
                "is_premium": t.is_premium,
                "premium_price": t.premium_price,
                "is_featured": t.is_featured,
                "usage_count": t.usage_count,
            }
            for t in templates
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    }


@router.get("/templates/{template_id}")
async def get_template_detail_customer(
    template_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full template details including design data (customer view)"""
    result = await db.execute(
        select(DesignTemplate).where(
            DesignTemplate.id == template_id,
            DesignTemplate.is_active == True
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": str(template.id),
        "name": template.name,
        "slug": template.slug,
        "description": template.description,
        "category": template.category,
        "style": template.style,
        "tags": template.tags or [],
        "design_data": template.design_data,
        "thumbnail": template.thumbnail_url,
        "preview_images": template.preview_images or [],
        "compatible_products": template.compatible_products or [],
        "is_premium": template.is_premium,
        "premium_price": template.premium_price,
        "usage_count": template.usage_count,
    }


@router.get("/products/{product_id}/templates")
async def get_product_templates(
    product_id: str,
    category: Optional[str] = None,
    style: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get design templates compatible with a specific product.
    
    Returns templates that are either:
    - Specifically compatible with this product ID
    - Compatible with this product's category
    - Universal templates (empty compatible_products list)
    """
    # Get product
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get compatible templates
    query = select(DesignTemplate).where(
        DesignTemplate.is_active == True
    )
    
    # Apply category/style filters
    if category:
        query = query.where(DesignTemplate.category == category)
    if style:
        query = query.where(DesignTemplate.style == style)
    
    # Order by popularity and featured
    query = query.order_by(
        DesignTemplate.is_featured.desc(),
        DesignTemplate.popularity_score.desc()
    )
    
    result = await db.execute(query)
    all_templates = result.scalars().all()
    
    # Filter by compatibility
    compatible_templates = []
    for template in all_templates:
        compatible_products = template.compatible_products or []
        
        # Universal template (no restrictions)
        if not compatible_products:
            compatible_templates.append(template)
            continue
        
        # Check if product ID or category is in compatible list
        if str(product_id) in compatible_products or product.category.slug in compatible_products:
            compatible_templates.append(template)
    
    # Group by category
    grouped = {}
    for template in compatible_templates:
        if template.category not in grouped:
            grouped[template.category] = []
        
        grouped[template.category].append({
            "id": str(template.id),
            "name": template.name,
            "slug": template.slug,
            "thumbnail": template.thumbnail_url,
            "style": template.style,
            "is_premium": template.is_premium,
            "premium_price": template.premium_price,
            "is_featured": template.is_featured,
        })
    
    return {
        "product_id": str(product_id),
        "product_name": product.name,
        "templates_by_category": grouped,
        "total_templates": len(compatible_templates),
    }
