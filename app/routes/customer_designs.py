"""Customer design management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
from pathlib import Path
import uuid as uuid_module

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.design_template import DesignTemplate, CustomerDesign
from app.models.product import Product
from app.models.logo_upload import LogoUpload, LogoOverlayConfig, ProductMockupTemplate
from app.services.logo_processing import LogoProcessingService
from app.services.storage import StorageService
from app.services.design_renderer import render_design_to_bytes
from app.config import settings

router = APIRouter(prefix="/api/designs", tags=["customer-designs"])


@router.post("/create")
async def create_customer_design(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new customer design from a template.
    
    Required fields:
    - template_id: UUID of the design template
    - product_id: UUID of the product
    - design_data: Modified design data (JSONB)
    
    Optional fields:
    - name: Custom name for the design
    """
    # Validate required fields
    required_fields = ['template_id', 'product_id', 'design_data']
    for field in required_fields:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Verify template exists and is active
    result = await db.execute(
        select(DesignTemplate).where(
            DesignTemplate.id == body['template_id'],
            DesignTemplate.is_active == True
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or inactive")
    
    # Verify product exists
    result = await db.execute(
        select(Product).where(Product.id == body['product_id'])
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Validate design_data structure
    design_data = body['design_data']
    if not isinstance(design_data, dict):
        raise HTTPException(status_code=400, detail="design_data must be a JSON object")
    
    if 'layers' not in design_data:
        raise HTTPException(status_code=400, detail="design_data must contain 'layers' array")
    
    # Create customer design
    design = CustomerDesign(
        user_id=user.id,
        template_id=template.id,
        product_id=product.id,
        design_data=design_data,
        name=body.get('name'),
        status='draft',
    )
    
    db.add(design)

    # Render a preview PNG from the design data and store it
    preview_url = None
    try:
        image_bytes = render_design_to_bytes(design_data)
        upload_dir = Path(settings.upload_dir) / "designs" / str(design.id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / "preview.png"
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        preview_url = f"/uploads/designs/{design.id}/preview.png"
        design.preview_url = preview_url
    except Exception as e:
        # Non-fatal: design is still created even if rendering fails
        import logging
        logging.warning(f"Failed to render design preview: {e}")

    # Increment template usage count
    template.usage_count += 1

    # Update popularity score (simple algorithm: usage_count * 0.1)
    template.popularity_score = template.usage_count * 0.1

    await db.commit()
    await db.refresh(design)

    return {
        "id": str(design.id),
        "message": "Design created successfully",
        "design": {
            "id": str(design.id),
            "name": design.name,
            "template_id": str(design.template_id),
            "product_id": str(design.product_id),
            "status": design.status,
            "preview_url": preview_url,
            "created_at": design.created_at.isoformat(),
        }
    }


@router.post("/render")
async def render_customer_design(
    body: dict,
    user: User = Depends(get_current_user),
):
    """Render arbitrary design_data to a PNG and return it directly."""
    design_data = body.get("design_data")
    if not isinstance(design_data, dict):
        raise HTTPException(status_code=400, detail="design_data must be a JSON object")
    try:
        image_bytes = render_design_to_bytes(design_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render design: {str(e)}")
    return Response(content=image_bytes, media_type="image/png")


@router.get("")
async def list_customer_designs(
    status: Optional[str] = None,
    product_id: Optional[str] = None,
    template_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all designs for the current user.
    
    Supports filtering by:
    - status: draft, saved, ordered, archived
    - product_id: Filter by product
    - template_id: Filter by template
    - search: Search in design name
    """
    query = select(CustomerDesign).options(
        selectinload(CustomerDesign.template),
        selectinload(CustomerDesign.product),
        selectinload(CustomerDesign.logo_overlays)
    ).where(CustomerDesign.user_id == user.id)
    
    # Apply filters
    if status:
        query = query.where(CustomerDesign.status == status)
    if product_id:
        query = query.where(CustomerDesign.product_id == product_id)
    if template_id:
        query = query.where(CustomerDesign.template_id == template_id)
    if search:
        query = query.where(CustomerDesign.name.ilike(f"%{search}%"))
    
    # Order by most recent
    query = query.order_by(CustomerDesign.updated_at.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        query.offset((page - 1) * limit).limit(limit)
    )
    designs = result.scalars().all()
    
    return {
        "designs": [
            {
                "id": str(d.id),
                "name": d.name,
                "template": {
                    "id": str(d.template.id),
                    "name": d.template.name,
                    "thumbnail": d.template.thumbnail_url,
                } if d.template else None,
                "product": {
                    "id": str(d.product.id),
                    "name": d.product.name,
                } if d.product else None,
                "preview_url": d.preview_url,
                "status": d.status,
                "logo_count": len(d.logo_overlays),
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
            for d in designs
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    }


@router.get("/{design_id}")
async def get_customer_design(
    design_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full design details including design data and logo overlays"""
    result = await db.execute(
        select(CustomerDesign)
        .options(
            selectinload(CustomerDesign.template),
            selectinload(CustomerDesign.product),
            selectinload(CustomerDesign.logo_overlays).selectinload(LogoOverlayConfig.logo_upload)
        )
        .where(
            CustomerDesign.id == design_id,
            CustomerDesign.user_id == user.id
        )
    )
    design = result.scalar_one_or_none()
    
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    return {
        "id": str(design.id),
        "name": design.name,
        "template": {
            "id": str(design.template.id),
            "name": design.template.name,
            "category": design.template.category,
            "thumbnail": design.template.thumbnail_url,
        } if design.template else None,
        "product": {
            "id": str(design.product.id),
            "name": design.product.name,
            "slug": design.product.slug,
        } if design.product else None,
        "design_data": design.design_data,
        "preview_url": design.preview_url,
        "status": design.status,
        "logo_overlays": [
            {
                "id": str(overlay.id),
                "logo": {
                    "id": str(overlay.logo_upload.id),
                    "name": overlay.logo_upload.name,
                    "thumbnail_url": overlay.logo_upload.thumbnail_url,
                    "optimized_url": overlay.logo_upload.optimized_url,
                } if overlay.logo_upload else None,
                "position_x": overlay.position_x,
                "position_y": overlay.position_y,
                "scale": overlay.scale,
                "rotation": overlay.rotation,
                "opacity": overlay.opacity,
                "z_index": overlay.z_index,
            }
            for overlay in design.logo_overlays
        ],
        "created_at": design.created_at.isoformat(),
        "updated_at": design.updated_at.isoformat() if design.updated_at else None,
    }


@router.put("/{design_id}")
async def update_customer_design(
    design_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a customer design.
    
    Can update:
    - design_data: Modified design data
    - name: Design name
    - status: Design status (draft, saved, ordered, archived)
    """
    result = await db.execute(
        select(CustomerDesign).where(
            CustomerDesign.id == design_id,
            CustomerDesign.user_id == user.id
        )
    )
    design = result.scalar_one_or_none()
    
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    # Update fields
    if 'design_data' in body:
        design.design_data = body['design_data']
    if 'name' in body:
        design.name = body['name']
    if 'status' in body:
        design.status = body['status']
    
    await db.commit()
    
    return {
        "message": "Design updated successfully",
        "design": {
            "id": str(design.id),
            "name": design.name,
            "status": design.status,
        }
    }


@router.delete("/{design_id}")
async def delete_customer_design(
    design_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a customer design"""
    result = await db.execute(
        select(CustomerDesign).where(
            CustomerDesign.id == design_id,
            CustomerDesign.user_id == user.id
        )
    )
    design = result.scalar_one_or_none()
    
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    # Check if design is in an order
    if design.status == 'ordered':
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a design that has been ordered. Archive it instead."
        )
    
    # Delete preview file if exists
    if design.preview_url:
        storage_service = StorageService()
        await storage_service.delete_file(design.preview_url)
    
    # Delete design (cascades to logo overlays)
    await db.delete(design)
    await db.commit()
    
    return {"message": "Design deleted successfully"}


@router.post("/{design_id}/duplicate")
async def duplicate_customer_design(
    design_id: str,
    new_name: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate an existing design"""
    result = await db.execute(
        select(CustomerDesign)
        .options(selectinload(CustomerDesign.logo_overlays))
        .where(
            CustomerDesign.id == design_id,
            CustomerDesign.user_id == user.id
        )
    )
    original = result.scalar_one_or_none()
    
    if not original:
        raise HTTPException(status_code=404, detail="Design not found")
    
    # Create duplicate
    duplicate = CustomerDesign(
        user_id=user.id,
        template_id=original.template_id,
        product_id=original.product_id,
        design_data=original.design_data,
        name=new_name or f"{original.name} (Copy)" if original.name else "Copy",
        status='draft',
    )
    
    db.add(duplicate)
    await db.flush()  # Get the ID
    
    # Duplicate logo overlays
    for overlay in original.logo_overlays:
        duplicate_overlay = LogoOverlayConfig(
            customer_design_id=duplicate.id,
            logo_upload_id=overlay.logo_upload_id,
            position_x=overlay.position_x,
            position_y=overlay.position_y,
            scale=overlay.scale,
            rotation=overlay.rotation,
            opacity=overlay.opacity,
            flip_horizontal=overlay.flip_horizontal,
            flip_vertical=overlay.flip_vertical,
            brightness=overlay.brightness,
            contrast=overlay.contrast,
            saturation=overlay.saturation,
            color_overlay=overlay.color_overlay,
            color_overlay_opacity=overlay.color_overlay_opacity,
            remove_background=overlay.remove_background,
            background_color=overlay.background_color,
            border_width=overlay.border_width,
            border_color=overlay.border_color,
            shadow_enabled=overlay.shadow_enabled,
            shadow_blur=overlay.shadow_blur,
            shadow_offset_x=overlay.shadow_offset_x,
            shadow_offset_y=overlay.shadow_offset_y,
            shadow_color=overlay.shadow_color,
            z_index=overlay.z_index,
            lock_aspect_ratio=overlay.lock_aspect_ratio,
            min_scale=overlay.min_scale,
            max_scale=overlay.max_scale,
        )
        db.add(duplicate_overlay)
    
    await db.commit()
    await db.refresh(duplicate)
    
    return {
        "id": str(duplicate.id),
        "message": "Design duplicated successfully",
        "design": {
            "id": str(duplicate.id),
            "name": duplicate.name,
        }
    }


@router.post("/{design_id}/add-logo")
async def add_logo_to_design(
    design_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a logo to a customer design with overlay configuration.
    
    Required fields:
    - logo_id: UUID of the logo upload
    
    Optional fields (overlay configuration):
    - position_x: 0-1 (default: 0.5)
    - position_y: 0-1 (default: 0.5)
    - scale: 0.05-0.8 (default: 0.2)
    - rotation: 0-360 (default: 0)
    - opacity: 0-1 (default: 1.0)
    - z_index: Layer order (default: 0)
    - ... (all other overlay config fields)
    """
    # Verify design ownership
    result = await db.execute(
        select(CustomerDesign).where(
            CustomerDesign.id == design_id,
            CustomerDesign.user_id == user.id
        )
    )
    design = result.scalar_one_or_none()
    
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    # Verify logo ownership
    if 'logo_id' not in body:
        raise HTTPException(status_code=400, detail="Missing required field: logo_id")
    
    result = await db.execute(
        select(LogoUpload).where(
            LogoUpload.id == body['logo_id'],
            LogoUpload.user_id == user.id,
            LogoUpload.status == 'active'
        )
    )
    logo = result.scalar_one_or_none()
    
    if not logo:
        raise HTTPException(status_code=404, detail="Logo not found")
    
    # Create overlay configuration
    overlay = LogoOverlayConfig(
        customer_design_id=design.id,
        logo_upload_id=logo.id,
        position_x=body.get('position_x', 0.5),
        position_y=body.get('position_y', 0.5),
        scale=body.get('scale', 0.2),
        rotation=body.get('rotation', 0.0),
        opacity=body.get('opacity', 1.0),
        flip_horizontal=body.get('flip_horizontal', False),
        flip_vertical=body.get('flip_vertical', False),
        brightness=body.get('brightness', 1.0),
        contrast=body.get('contrast', 1.0),
        saturation=body.get('saturation', 1.0),
        color_overlay=body.get('color_overlay'),
        color_overlay_opacity=body.get('color_overlay_opacity', 0.0),
        remove_background=body.get('remove_background', False),
        background_color=body.get('background_color'),
        border_width=body.get('border_width', 0),
        border_color=body.get('border_color'),
        shadow_enabled=body.get('shadow_enabled', False),
        shadow_blur=body.get('shadow_blur', 10),
        shadow_offset_x=body.get('shadow_offset_x', 5),
        shadow_offset_y=body.get('shadow_offset_y', 5),
        shadow_color=body.get('shadow_color', '#00000080'),
        z_index=body.get('z_index', 0),
        lock_aspect_ratio=body.get('lock_aspect_ratio', True),
        min_scale=body.get('min_scale', 0.05),
        max_scale=body.get('max_scale', 0.8),
    )
    
    db.add(overlay)
    
    # Update logo usage
    logo.usage_count += 1
    logo.last_used_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(overlay)
    
    return {
        "id": str(overlay.id),
        "message": "Logo added to design successfully",
        "overlay": {
            "id": str(overlay.id),
            "logo_id": str(overlay.logo_upload_id),
            "position_x": overlay.position_x,
            "position_y": overlay.position_y,
            "scale": overlay.scale,
        }
    }


@router.put("/{design_id}/logos/{overlay_id}")
async def update_logo_overlay(
    design_id: str,
    overlay_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update logo overlay configuration"""
    # Verify design ownership
    result = await db.execute(
        select(CustomerDesign).where(
            CustomerDesign.id == design_id,
            CustomerDesign.user_id == user.id
        )
    )
    design = result.scalar_one_or_none()
    
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    # Get overlay
    result = await db.execute(
        select(LogoOverlayConfig).where(
            LogoOverlayConfig.id == overlay_id,
            LogoOverlayConfig.customer_design_id == design_id
        )
    )
    overlay = result.scalar_one_or_none()
    
    if not overlay:
        raise HTTPException(status_code=404, detail="Logo overlay not found")
    
    # Update fields
    updatable_fields = [
        'position_x', 'position_y', 'scale', 'rotation', 'opacity',
        'flip_horizontal', 'flip_vertical', 'brightness', 'contrast', 'saturation',
        'color_overlay', 'color_overlay_opacity', 'remove_background', 'background_color',
        'border_width', 'border_color', 'shadow_enabled', 'shadow_blur',
        'shadow_offset_x', 'shadow_offset_y', 'shadow_color', 'z_index',
        'lock_aspect_ratio', 'min_scale', 'max_scale'
    ]
    
    for field in updatable_fields:
        if field in body:
            setattr(overlay, field, body[field])
    
    await db.commit()
    
    return {"message": "Logo overlay updated successfully"}


@router.delete("/{design_id}/logos/{overlay_id}")
async def remove_logo_from_design(
    design_id: str,
    overlay_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a logo from a design"""
    # Verify design ownership
    result = await db.execute(
        select(CustomerDesign).where(
            CustomerDesign.id == design_id,
            CustomerDesign.user_id == user.id
        )
    )
    design = result.scalar_one_or_none()
    
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    # Get overlay
    result = await db.execute(
        select(LogoOverlayConfig).where(
            LogoOverlayConfig.id == overlay_id,
            LogoOverlayConfig.customer_design_id == design_id
        )
    )
    overlay = result.scalar_one_or_none()
    
    if not overlay:
        raise HTTPException(status_code=404, detail="Logo overlay not found")
    
    await db.delete(overlay)
    await db.commit()
    
    return {"message": "Logo removed from design successfully"}


@router.post("/{design_id}/generate-preview")
async def generate_design_preview(
    design_id: str,
    mockup_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a preview image of the design with logo overlays on product mockup.
    
    If mockup_id is not provided, uses the primary mockup for the product.
    Returns the preview URL.
    """
    # Get design with all related data
    result = await db.execute(
        select(CustomerDesign)
        .options(
            selectinload(CustomerDesign.product),
            selectinload(CustomerDesign.logo_overlays).selectinload(LogoOverlayConfig.logo_upload)
        )
        .where(
            CustomerDesign.id == design_id,
            CustomerDesign.user_id == user.id
        )
    )
    design = result.scalar_one_or_none()
    
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    # Get mockup template
    if mockup_id:
        result = await db.execute(
            select(ProductMockupTemplate).where(
                ProductMockupTemplate.id == mockup_id,
                ProductMockupTemplate.product_id == design.product_id
            )
        )
        mockup = result.scalar_one_or_none()
        
        if not mockup:
            raise HTTPException(status_code=404, detail="Mockup template not found for this product")
    else:
        # Get primary mockup for product
        result = await db.execute(
            select(ProductMockupTemplate).where(
                ProductMockupTemplate.product_id == design.product_id,
                ProductMockupTemplate.is_primary == True
            )
        )
        mockup = result.scalar_one_or_none()
        
        if not mockup:
            # Fallback to any mockup for this product
            result = await db.execute(
                select(ProductMockupTemplate)
                .where(ProductMockupTemplate.product_id == design.product_id)
                .order_by(ProductMockupTemplate.sort_order)
                .limit(1)
            )
            mockup = result.scalar_one_or_none()
    
    if not mockup:
        raise HTTPException(
            status_code=404,
            detail="No mockup template found for this product. Please contact admin to add mockup templates."
        )
    
    # Get all logo overlays sorted by z_index
    overlays = sorted(design.logo_overlays, key=lambda x: x.z_index)
    
    if not overlays:
        raise HTTPException(
            status_code=400,
            detail="No logos added to this design. Add at least one logo to generate preview."
        )
    
    try:
        # Start with base mockup image
        import httpx
        from PIL import Image
        import io
        
        async with httpx.AsyncClient() as client:
            mockup_response = await client.get(mockup.mockup_image_url)
            if mockup_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to download mockup image")
            
            mockup_image = Image.open(io.BytesIO(mockup_response.content))
            mockup_image = mockup_image.convert('RGBA')
        
        # Apply each logo overlay
        processing_service = LogoProcessingService()
        
        for overlay in overlays:
            if not overlay.logo_upload:
                continue
            
            # Use optimized version if available, otherwise original
            logo_url = overlay.logo_upload.optimized_url or overlay.logo_upload.file_url
            
            # Apply logo overlay to mockup
            mockup_bytes = io.BytesIO()
            mockup_image.save(mockup_bytes, format='PNG')
            mockup_bytes.seek(0)
            
            # Generate preview with this logo
            preview_bytes = await processing_service.apply_logo_overlay(
                mockup.mockup_image_url,
                logo_url,
                overlay,
                mockup.design_area
            )
            
            # Load the result for next iteration
            mockup_image = Image.open(io.BytesIO(preview_bytes))
            mockup_image = mockup_image.convert('RGBA')
        
        # Save final preview
        final_output = io.BytesIO()
        mockup_image.convert('RGB').save(final_output, format='JPEG', quality=90, optimize=True)
        final_bytes = final_output.getvalue()
        
        # Upload to storage
        storage_service = StorageService()
        preview_url = await storage_service.save_preview(
            final_bytes,
            design.id,
            mockup.id
        )
        
        # Update design with preview URL
        design.preview_url = preview_url
        await db.commit()
        
        return {
            "preview_url": preview_url,
            "mockup_id": str(mockup.id),
            "mockup_name": mockup.name,
            "message": "Preview generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate preview: {str(e)}"
        )


@router.get("/{design_id}/previews")
async def get_design_previews(
    design_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all available mockup templates for a design's product.
    Useful for generating previews from different angles.
    """
    # Get design
    result = await db.execute(
        select(CustomerDesign)
        .options(selectinload(CustomerDesign.product))
        .where(
            CustomerDesign.id == design_id,
            CustomerDesign.user_id == user.id
        )
    )
    design = result.scalar_one_or_none()
    
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    # Get all mockups for this product
    result = await db.execute(
        select(ProductMockupTemplate)
        .where(ProductMockupTemplate.product_id == design.product_id)
        .order_by(ProductMockupTemplate.sort_order)
    )
    mockups = result.scalars().all()
    
    return {
        "design_id": str(design.id),
        "product_id": str(design.product_id),
        "product_name": design.product.name if design.product else None,
        "current_preview": design.preview_url,
        "available_mockups": [
            {
                "id": str(m.id),
                "name": m.name,
                "view_type": m.view_type,
                "is_primary": m.is_primary,
                "mockup_image_url": m.mockup_image_url,
            }
            for m in mockups
        ]
    }


@router.get("/stats/overview")
async def get_design_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get design statistics for the current user"""
    
    # Total designs
    result = await db.execute(
        select(func.count())
        .select_from(CustomerDesign)
        .where(CustomerDesign.user_id == user.id)
    )
    total_designs = result.scalar()
    
    # Designs by status
    result = await db.execute(
        select(
            CustomerDesign.status,
            func.count().label('count')
        )
        .where(CustomerDesign.user_id == user.id)
        .group_by(CustomerDesign.status)
    )
    by_status = {row[0]: row[1] for row in result.all()}
    
    # Recent designs
    result = await db.execute(
        select(CustomerDesign)
        .options(
            selectinload(CustomerDesign.template),
            selectinload(CustomerDesign.product)
        )
        .where(CustomerDesign.user_id == user.id)
        .order_by(CustomerDesign.updated_at.desc())
        .limit(5)
    )
    recent = result.scalars().all()
    
    return {
        "overview": {
            "total_designs": total_designs,
            "draft": by_status.get('draft', 0),
            "saved": by_status.get('saved', 0),
            "ordered": by_status.get('ordered', 0),
            "archived": by_status.get('archived', 0),
        },
        "recent_designs": [
            {
                "id": str(d.id),
                "name": d.name,
                "template_name": d.template.name if d.template else None,
                "product_name": d.product.name if d.product else None,
                "preview_url": d.preview_url,
                "status": d.status,
                "updated_at": d.updated_at.isoformat() if d.updated_at else d.created_at.isoformat(),
            }
            for d in recent
        ]
    }
