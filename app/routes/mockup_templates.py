"""Product mockup template management endpoints (Admin)"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from typing import Optional

from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.user import User
from app.models.product import Product
from app.models.logo_upload import ProductMockupTemplate
from app.services.storage import StorageService
from app.services.audit import log_audit

router = APIRouter(prefix="/api/admin/mockups", tags=["mockup-templates"])


@router.get("")
async def list_mockup_templates(
    product_id: Optional[str] = None,
    view_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List all mockup templates.
    
    Supports filtering by:
    - product_id: Filter by product
    - view_type: Filter by view type (front, back, side, angled, flat)
    """
    query = select(ProductMockupTemplate).options(
        selectinload(ProductMockupTemplate.product)
    )
    
    # Apply filters
    if product_id:
        query = query.where(ProductMockupTemplate.product_id == product_id)
    if view_type:
        query = query.where(ProductMockupTemplate.view_type == view_type)
    
    # Order by product and sort order
    query = query.order_by(
        ProductMockupTemplate.product_id,
        ProductMockupTemplate.sort_order
    )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        query.offset((page - 1) * limit).limit(limit)
    )
    mockups = result.scalars().all()
    
    return {
        "mockups": [
            {
                "id": str(m.id),
                "product": {
                    "id": str(m.product.id),
                    "name": m.product.name,
                    "slug": m.product.slug,
                } if m.product else None,
                "name": m.name,
                "mockup_image_url": m.mockup_image_url,
                "design_area": m.design_area,
                "view_type": m.view_type,
                "is_primary": m.is_primary,
                "sort_order": m.sort_order,
                "created_at": m.created_at.isoformat(),
            }
            for m in mockups
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    }


@router.post("")
async def create_mockup_template(
    product_id: str,
    name: str,
    view_type: str,
    design_area: str,  # JSON string
    mockup_image: UploadFile = File(...),
    is_primary: bool = False,
    sort_order: int = 0,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new mockup template.
    
    Required fields:
    - product_id: UUID of the product
    - name: Mockup name (e.g., "Front View", "Back View")
    - view_type: View type (front, back, side, angled, flat)
    - design_area: JSON string with design area definition
    - mockup_image: Mockup image file
    
    Optional fields:
    - is_primary: Mark as primary mockup (default: false)
    - sort_order: Display order (default: 0)
    
    Design area format:
    {
        "x": 100,
        "y": 100,
        "width": 800,
        "height": 800,
        "rotation": 0,
        "perspective": {  // Optional for 3D mockups
            "topLeft": [x, y],
            "topRight": [x, y],
            "bottomLeft": [x, y],
            "bottomRight": [x, y]
        }
    }
    """
    # Verify product exists
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Validate view_type
    valid_view_types = ['front', 'back', 'side', 'angled', 'flat']
    if view_type not in valid_view_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid view_type. Must be one of: {', '.join(valid_view_types)}"
        )
    
    # Parse design_area JSON
    import json
    try:
        design_area_dict = json.loads(design_area)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid design_area JSON")
    
    # Validate design_area structure
    required_fields = ['x', 'y', 'width', 'height']
    for field in required_fields:
        if field not in design_area_dict:
            raise HTTPException(
                status_code=400,
                detail=f"design_area missing required field: {field}"
            )
    
    # Validate mockup image
    if not mockup_image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read and upload mockup image
    file_content = await mockup_image.read()
    
    # Validate file size (max 20MB for mockup images)
    if len(file_content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 20MB limit")
    
    storage_service = StorageService()
    mockup_url = await storage_service.save_mockup_image(
        file_content,
        product.id,
        view_type
    )
    
    # If this is set as primary, unset other primary mockups for this product
    if is_primary:
        await db.execute(
            ProductMockupTemplate.__table__.update()
            .where(ProductMockupTemplate.product_id == product_id)
            .values(is_primary=False)
        )
    
    # Create mockup template
    mockup = ProductMockupTemplate(
        product_id=product.id,
        name=name,
        mockup_image_url=mockup_url,
        design_area=design_area_dict,
        view_type=view_type,
        is_primary=is_primary,
        sort_order=sort_order,
    )
    
    db.add(mockup)
    await db.commit()
    await db.refresh(mockup)
    
    # Log admin action
    await log_audit(
        db=db,
        admin_id=admin.id,
        action="create_mockup_template",
        resource_type="mockup_template",
        resource_id=str(mockup.id),
        changes={
            "product_id": str(product.id),
            "product_name": product.name,
            "name": name,
            "view_type": view_type
        }
    )
    
    return {
        "id": str(mockup.id),
        "message": "Mockup template created successfully",
        "mockup": {
            "id": str(mockup.id),
            "name": mockup.name,
            "view_type": mockup.view_type,
            "mockup_image_url": mockup.mockup_image_url,
        }
    }


@router.get("/{mockup_id}")
async def get_mockup_template(
    mockup_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get mockup template details"""
    result = await db.execute(
        select(ProductMockupTemplate)
        .options(selectinload(ProductMockupTemplate.product))
        .where(ProductMockupTemplate.id == mockup_id)
    )
    mockup = result.scalar_one_or_none()
    
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup template not found")
    
    return {
        "id": str(mockup.id),
        "product": {
            "id": str(mockup.product.id),
            "name": mockup.product.name,
            "slug": mockup.product.slug,
        } if mockup.product else None,
        "name": mockup.name,
        "mockup_image_url": mockup.mockup_image_url,
        "design_area": mockup.design_area,
        "view_type": mockup.view_type,
        "is_primary": mockup.is_primary,
        "sort_order": mockup.sort_order,
        "created_at": mockup.created_at.isoformat(),
    }


@router.put("/{mockup_id}")
async def update_mockup_template(
    mockup_id: str,
    name: Optional[str] = None,
    view_type: Optional[str] = None,
    design_area: Optional[str] = None,  # JSON string
    is_primary: Optional[bool] = None,
    sort_order: Optional[int] = None,
    mockup_image: Optional[UploadFile] = File(None),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a mockup template.
    
    All fields are optional. Only provided fields will be updated.
    """
    result = await db.execute(
        select(ProductMockupTemplate).where(ProductMockupTemplate.id == mockup_id)
    )
    mockup = result.scalar_one_or_none()
    
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup template not found")
    
    # Track changes
    changes = {}
    
    # Update name
    if name is not None:
        changes['name'] = {"old": mockup.name, "new": name}
        mockup.name = name
    
    # Update view_type
    if view_type is not None:
        valid_view_types = ['front', 'back', 'side', 'angled', 'flat']
        if view_type not in valid_view_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid view_type. Must be one of: {', '.join(valid_view_types)}"
            )
        changes['view_type'] = {"old": mockup.view_type, "new": view_type}
        mockup.view_type = view_type
    
    # Update design_area
    if design_area is not None:
        import json
        try:
            design_area_dict = json.loads(design_area)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid design_area JSON")
        
        # Validate design_area structure
        required_fields = ['x', 'y', 'width', 'height']
        for field in required_fields:
            if field not in design_area_dict:
                raise HTTPException(
                    status_code=400,
                    detail=f"design_area missing required field: {field}"
                )
        
        changes['design_area'] = {"old": mockup.design_area, "new": design_area_dict}
        mockup.design_area = design_area_dict
    
    # Update is_primary
    if is_primary is not None:
        if is_primary and not mockup.is_primary:
            # Unset other primary mockups for this product
            await db.execute(
                ProductMockupTemplate.__table__.update()
                .where(
                    ProductMockupTemplate.product_id == mockup.product_id,
                    ProductMockupTemplate.id != mockup_id
                )
                .values(is_primary=False)
            )
        changes['is_primary'] = {"old": mockup.is_primary, "new": is_primary}
        mockup.is_primary = is_primary
    
    # Update sort_order
    if sort_order is not None:
        changes['sort_order'] = {"old": mockup.sort_order, "new": sort_order}
        mockup.sort_order = sort_order
    
    # Update mockup image
    if mockup_image:
        if not mockup_image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        file_content = await mockup_image.read()
        
        if len(file_content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 20MB limit")
        
        # Delete old image
        storage_service = StorageService()
        if mockup.mockup_image_url:
            await storage_service.delete_file(mockup.mockup_image_url)
        
        # Upload new image
        result = await db.execute(
            select(Product).where(Product.id == mockup.product_id)
        )
        product = result.scalar_one()
        
        mockup_url = await storage_service.save_mockup_image(
            file_content,
            product.id,
            mockup.view_type
        )
        
        changes['mockup_image_url'] = {"old": mockup.mockup_image_url, "new": mockup_url}
        mockup.mockup_image_url = mockup_url
    
    await db.commit()
    
    # Log admin action
    if changes:
        await log_audit(
            db=db,
            admin_id=admin.id,
            action="update_mockup_template",
            resource_type="mockup_template",
            resource_id=str(mockup.id),
            changes=changes
        )
    
    return {
        "message": "Mockup template updated successfully",
        "changes": list(changes.keys())
    }


@router.delete("/{mockup_id}")
async def delete_mockup_template(
    mockup_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a mockup template"""
    result = await db.execute(
        select(ProductMockupTemplate).where(ProductMockupTemplate.id == mockup_id)
    )
    mockup = result.scalar_one_or_none()
    
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup template not found")
    
    # Delete mockup image from storage
    storage_service = StorageService()
    if mockup.mockup_image_url:
        await storage_service.delete_file(mockup.mockup_image_url)
    
    # Delete from database
    await db.delete(mockup)
    await db.commit()
    
    # Log admin action
    await log_audit(
        db=db,
        admin_id=admin.id,
        action="delete_mockup_template",
        resource_type="mockup_template",
        resource_id=str(mockup.id),
        changes={"name": mockup.name, "view_type": mockup.view_type}
    )
    
    return {"message": "Mockup template deleted successfully"}


@router.get("/products/{product_id}/mockups")
async def get_product_mockups(
    product_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all mockup templates for a specific product"""
    # Verify product exists
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get all mockups for this product
    result = await db.execute(
        select(ProductMockupTemplate)
        .where(ProductMockupTemplate.product_id == product_id)
        .order_by(ProductMockupTemplate.sort_order)
    )
    mockups = result.scalars().all()
    
    return {
        "product": {
            "id": str(product.id),
            "name": product.name,
            "slug": product.slug,
        },
        "mockups": [
            {
                "id": str(m.id),
                "name": m.name,
                "mockup_image_url": m.mockup_image_url,
                "design_area": m.design_area,
                "view_type": m.view_type,
                "is_primary": m.is_primary,
                "sort_order": m.sort_order,
            }
            for m in mockups
        ],
        "total": len(mockups)
    }


@router.post("/{mockup_id}/set-primary")
async def set_primary_mockup(
    mockup_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Set a mockup as the primary mockup for its product"""
    result = await db.execute(
        select(ProductMockupTemplate).where(ProductMockupTemplate.id == mockup_id)
    )
    mockup = result.scalar_one_or_none()
    
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup template not found")
    
    # Unset other primary mockups for this product
    await db.execute(
        ProductMockupTemplate.__table__.update()
        .where(
            ProductMockupTemplate.product_id == mockup.product_id,
            ProductMockupTemplate.id != mockup_id
        )
        .values(is_primary=False)
    )
    
    # Set this mockup as primary
    mockup.is_primary = True
    await db.commit()
    
    # Log admin action
    await log_audit(
        db=db,
        admin_id=admin.id,
        action="set_primary_mockup",
        resource_type="mockup_template",
        resource_id=str(mockup.id),
        changes={"name": mockup.name}
    )
    
    return {"message": f"Mockup '{mockup.name}' set as primary"}


@router.post("/bulk-reorder")
async def bulk_reorder_mockups(
    mockup_orders: list[dict],  # [{"id": "uuid", "sort_order": 0}, ...]
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk update sort order for multiple mockups.
    
    Body: [
        {"id": "mockup-uuid-1", "sort_order": 0},
        {"id": "mockup-uuid-2", "sort_order": 1},
        ...
    ]
    """
    if not mockup_orders:
        raise HTTPException(status_code=400, detail="No mockup orders provided")
    
    updated_count = 0
    
    for item in mockup_orders:
        if 'id' not in item or 'sort_order' not in item:
            continue
        
        result = await db.execute(
            select(ProductMockupTemplate).where(ProductMockupTemplate.id == item['id'])
        )
        mockup = result.scalar_one_or_none()
        
        if mockup:
            mockup.sort_order = item['sort_order']
            updated_count += 1
    
    await db.commit()
    
    # Log admin action
    await log_audit(
        db=db,
        admin_id=admin.id,
        action="bulk_reorder_mockups",
        resource_type="mockup_template",
        resource_id="bulk",
        changes={"count": updated_count}
    )
    
    return {
        "message": f"Updated sort order for {updated_count} mockups",
        "updated_count": updated_count
    }


@router.get("/stats/overview")
async def get_mockup_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get mockup template statistics"""
    
    # Total mockups
    result = await db.execute(
        select(func.count()).select_from(ProductMockupTemplate)
    )
    total_mockups = result.scalar()
    
    # Mockups by view type
    result = await db.execute(
        select(
            ProductMockupTemplate.view_type,
            func.count().label('count')
        )
        .group_by(ProductMockupTemplate.view_type)
        .order_by(func.count().desc())
    )
    by_view_type = [{"view_type": row[0], "count": row[1]} for row in result.all()]
    
    # Products with mockups
    result = await db.execute(
        select(func.count(func.distinct(ProductMockupTemplate.product_id)))
        .select_from(ProductMockupTemplate)
    )
    products_with_mockups = result.scalar()
    
    # Products without mockups
    result = await db.execute(
        select(func.count()).select_from(Product)
    )
    total_products = result.scalar()
    
    products_without_mockups = total_products - products_with_mockups
    
    return {
        "overview": {
            "total_mockups": total_mockups,
            "products_with_mockups": products_with_mockups,
            "products_without_mockups": products_without_mockups,
            "total_products": total_products,
        },
        "by_view_type": by_view_type
    }
