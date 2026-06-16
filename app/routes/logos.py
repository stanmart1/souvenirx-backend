"""Logo upload and management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.logo_upload import LogoUpload
from app.services.logo_processing import LogoProcessingService
from app.services.storage import StorageService

router = APIRouter(prefix="/api/logos", tags=["logos"])


@router.post("/upload")
async def upload_logo(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo file.
    
    Supported formats: PNG, JPG, JPEG, SVG, WebP
    Max size: 10MB
    
    The logo will be processed to generate:
    - Thumbnail (200x200)
    - Optimized version (max 1000x1000)
    - Transparent version (background removed, if applicable)
    - Dominant colors extracted
    """
    # Read file content
    file_content = await file.read()
    
    # Validate file
    is_valid, error_message = LogoProcessingService.validate_logo_file(
        file_content,
        file.filename,
        file.content_type
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    
    try:
        # Process logo
        processing_service = LogoProcessingService()
        processed_data = await processing_service.process_logo_upload(
            file_content,
            file.filename,
            file.content_type
        )
        
        # Save files to storage
        storage_service = StorageService()
        
        # Save original
        file_url = await storage_service.save_logo(
            processed_data['file_content'],
            file.filename,
            user.id,
            'original'
        )
        
        # Save thumbnail
        thumbnail_url = None
        if processed_data['thumbnail_content']:
            thumbnail_url = await storage_service.save_logo(
                processed_data['thumbnail_content'],
                file.filename,
                user.id,
                'thumbnail'
            )
        
        # Save optimized
        optimized_url = None
        if processed_data['optimized_content']:
            optimized_url = await storage_service.save_logo(
                processed_data['optimized_content'],
                file.filename,
                user.id,
                'optimized'
            )
        
        # Save transparent
        transparent_url = None
        if processed_data['transparent_content']:
            transparent_url = await storage_service.save_logo(
                processed_data['transparent_content'],
                file.filename,
                user.id,
                'transparent'
            )
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # Create logo upload record
        logo_upload = LogoUpload(
            user_id=user.id,
            original_filename=file.filename,
            file_url=file_url,
            file_size=len(file_content),
            file_format=file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown',
            mime_type=file.content_type,
            width=processed_data['width'],
            height=processed_data['height'],
            aspect_ratio=processed_data['aspect_ratio'],
            thumbnail_url=thumbnail_url,
            optimized_url=optimized_url,
            transparent_url=transparent_url,
            has_transparency=processed_data['has_transparency'],
            dominant_colors=processed_data['dominant_colors'],
            is_vector=processed_data['is_vector'],
            processing_status='completed',
            name=name or file.filename,
            tags=tag_list,
        )
        
        db.add(logo_upload)
        await db.commit()
        await db.refresh(logo_upload)
        
        return {
            "id": str(logo_upload.id),
            "name": logo_upload.name,
            "file_url": logo_upload.file_url,
            "thumbnail_url": logo_upload.thumbnail_url,
            "optimized_url": logo_upload.optimized_url,
            "transparent_url": logo_upload.transparent_url,
            "width": logo_upload.width,
            "height": logo_upload.height,
            "aspect_ratio": logo_upload.aspect_ratio,
            "has_transparency": logo_upload.has_transparency,
            "dominant_colors": logo_upload.dominant_colors,
            "is_vector": logo_upload.is_vector,
            "file_size": logo_upload.file_size,
            "file_format": logo_upload.file_format,
            "tags": logo_upload.tags,
            "message": "Logo uploaded successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process logo: {str(e)}")


@router.get("/my-logos")
async def list_my_logos(
    status: str = Query("active", description="Filter by status: active, archived, deleted"),
    is_favorite: Optional[bool] = None,
    tags: Optional[str] = None,  # Comma-separated tags to filter
    search: Optional[str] = None,
    sort_by: str = Query("created_at", description="Sort by: created_at, name, usage_count, last_used_at"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all logos uploaded by the current user.
    
    Supports filtering by:
    - status: active, archived, deleted
    - is_favorite: true/false
    - tags: comma-separated list
    - search: search in name and filename
    
    Supports sorting by:
    - created_at (default)
    - name
    - usage_count
    - last_used_at
    """
    query = select(LogoUpload).where(
        LogoUpload.user_id == user.id,
        LogoUpload.status == status
    )
    
    # Apply filters
    if is_favorite is not None:
        query = query.where(LogoUpload.is_favorite == is_favorite)
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        # Filter logos that have any of the specified tags
        for tag in tag_list:
            query = query.where(LogoUpload.tags.contains([tag]))
    
    if search:
        query = query.where(
            or_(
                LogoUpload.name.ilike(f"%{search}%"),
                LogoUpload.original_filename.ilike(f"%{search}%")
            )
        )
    
    # Apply sorting
    sort_column = {
        'created_at': LogoUpload.created_at,
        'name': LogoUpload.name,
        'usage_count': LogoUpload.usage_count,
        'last_used_at': LogoUpload.last_used_at,
    }.get(sort_by, LogoUpload.created_at)
    
    if sort_order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        query.offset((page - 1) * limit).limit(limit)
    )
    logos = result.scalars().all()
    
    return {
        "logos": [
            {
                "id": str(logo.id),
                "name": logo.name,
                "original_filename": logo.original_filename,
                "thumbnail_url": logo.thumbnail_url,
                "file_url": logo.file_url,
                "optimized_url": logo.optimized_url,
                "transparent_url": logo.transparent_url,
                "width": logo.width,
                "height": logo.height,
                "aspect_ratio": logo.aspect_ratio,
                "file_format": logo.file_format,
                "file_size": logo.file_size,
                "has_transparency": logo.has_transparency,
                "dominant_colors": logo.dominant_colors,
                "is_vector": logo.is_vector,
                "is_favorite": logo.is_favorite,
                "tags": logo.tags or [],
                "usage_count": logo.usage_count,
                "last_used_at": logo.last_used_at.isoformat() if logo.last_used_at else None,
                "created_at": logo.created_at.isoformat(),
            }
            for logo in logos
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    }


@router.get("/logos/{logo_id}")
async def get_logo_details(
    logo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific logo"""
    result = await db.execute(
        select(LogoUpload).where(
            LogoUpload.id == logo_id,
            LogoUpload.user_id == user.id
        )
    )
    logo = result.scalar_one_or_none()
    
    if not logo:
        raise HTTPException(status_code=404, detail="Logo not found")
    
    return {
        "id": str(logo.id),
        "name": logo.name,
        "original_filename": logo.original_filename,
        "file_url": logo.file_url,
        "thumbnail_url": logo.thumbnail_url,
        "optimized_url": logo.optimized_url,
        "transparent_url": logo.transparent_url,
        "width": logo.width,
        "height": logo.height,
        "aspect_ratio": logo.aspect_ratio,
        "file_format": logo.file_format,
        "file_size": logo.file_size,
        "mime_type": logo.mime_type,
        "has_transparency": logo.has_transparency,
        "dominant_colors": logo.dominant_colors or [],
        "is_vector": logo.is_vector,
        "processing_status": logo.processing_status,
        "processing_error": logo.processing_error,
        "is_favorite": logo.is_favorite,
        "tags": logo.tags or [],
        "usage_count": logo.usage_count,
        "last_used_at": logo.last_used_at.isoformat() if logo.last_used_at else None,
        "status": logo.status,
        "created_at": logo.created_at.isoformat(),
        "updated_at": logo.updated_at.isoformat() if logo.updated_at else None,
    }


@router.put("/logos/{logo_id}")
async def update_logo(
    logo_id: str,
    name: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    is_favorite: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update logo metadata.
    
    Can update:
    - name: Display name
    - tags: Comma-separated list of tags
    - is_favorite: Mark as favorite
    """
    result = await db.execute(
        select(LogoUpload).where(
            LogoUpload.id == logo_id,
            LogoUpload.user_id == user.id
        )
    )
    logo = result.scalar_one_or_none()
    
    if not logo:
        raise HTTPException(status_code=404, detail="Logo not found")
    
    # Update fields
    if name is not None:
        logo.name = name
    
    if tags is not None:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        logo.tags = tag_list
    
    if is_favorite is not None:
        logo.is_favorite = is_favorite
    
    await db.commit()
    
    return {
        "message": "Logo updated successfully",
        "logo": {
            "id": str(logo.id),
            "name": logo.name,
            "tags": logo.tags,
            "is_favorite": logo.is_favorite,
        }
    }


@router.delete("/logos/{logo_id}")
async def delete_logo(
    logo_id: str,
    permanent: bool = Query(False, description="Permanently delete (true) or archive (false)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a logo.
    
    - permanent=false (default): Archive the logo (soft delete)
    - permanent=true: Permanently delete the logo and all files
    """
    result = await db.execute(
        select(LogoUpload).where(
            LogoUpload.id == logo_id,
            LogoUpload.user_id == user.id
        )
    )
    logo = result.scalar_one_or_none()
    
    if not logo:
        raise HTTPException(status_code=404, detail="Logo not found")
    
    if permanent:
        # Check if logo is being used in any designs
        from app.models.logo_upload import LogoOverlayConfig
        result = await db.execute(
            select(func.count())
            .select_from(LogoOverlayConfig)
            .where(LogoOverlayConfig.logo_upload_id == logo_id)
        )
        usage_count = result.scalar()
        
        if usage_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot permanently delete logo. It is being used in {usage_count} designs. Archive it instead."
            )
        
        # Delete files from storage
        storage_service = StorageService()
        if logo.file_url:
            await storage_service.delete_file(logo.file_url)
        if logo.thumbnail_url:
            await storage_service.delete_file(logo.thumbnail_url)
        if logo.optimized_url:
            await storage_service.delete_file(logo.optimized_url)
        if logo.transparent_url:
            await storage_service.delete_file(logo.transparent_url)
        
        # Delete from database
        await db.delete(logo)
        message = "Logo permanently deleted"
    else:
        # Soft delete (archive)
        logo.status = "archived"
        message = "Logo archived"
    
    await db.commit()
    
    return {"message": message}


@router.post("/logos/{logo_id}/restore")
async def restore_logo(
    logo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restore an archived logo"""
    result = await db.execute(
        select(LogoUpload).where(
            LogoUpload.id == logo_id,
            LogoUpload.user_id == user.id,
            LogoUpload.status == "archived"
        )
    )
    logo = result.scalar_one_or_none()
    
    if not logo:
        raise HTTPException(status_code=404, detail="Archived logo not found")
    
    logo.status = "active"
    await db.commit()
    
    return {"message": "Logo restored successfully"}


@router.get("/stats")
async def get_logo_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get logo statistics for the current user"""
    
    # Total logos
    result = await db.execute(
        select(func.count())
        .select_from(LogoUpload)
        .where(
            LogoUpload.user_id == user.id,
            LogoUpload.status == "active"
        )
    )
    total_logos = result.scalar()
    
    # Favorite logos
    result = await db.execute(
        select(func.count())
        .select_from(LogoUpload)
        .where(
            LogoUpload.user_id == user.id,
            LogoUpload.status == "active",
            LogoUpload.is_favorite == True
        )
    )
    favorite_logos = result.scalar()
    
    # Total storage used (in bytes)
    result = await db.execute(
        select(func.sum(LogoUpload.file_size))
        .select_from(LogoUpload)
        .where(
            LogoUpload.user_id == user.id,
            LogoUpload.status == "active"
        )
    )
    total_storage = result.scalar() or 0
    
    # Most used logos
    result = await db.execute(
        select(LogoUpload)
        .where(
            LogoUpload.user_id == user.id,
            LogoUpload.status == "active"
        )
        .order_by(LogoUpload.usage_count.desc())
        .limit(5)
    )
    most_used = result.scalars().all()
    
    # Recently uploaded
    result = await db.execute(
        select(LogoUpload)
        .where(
            LogoUpload.user_id == user.id,
            LogoUpload.status == "active"
        )
        .order_by(LogoUpload.created_at.desc())
        .limit(5)
    )
    recent = result.scalars().all()
    
    return {
        "overview": {
            "total_logos": total_logos,
            "favorite_logos": favorite_logos,
            "total_storage_bytes": total_storage,
            "total_storage_mb": round(total_storage / (1024 * 1024), 2),
        },
        "most_used": [
            {
                "id": str(logo.id),
                "name": logo.name,
                "thumbnail_url": logo.thumbnail_url,
                "usage_count": logo.usage_count,
            }
            for logo in most_used
        ],
        "recently_uploaded": [
            {
                "id": str(logo.id),
                "name": logo.name,
                "thumbnail_url": logo.thumbnail_url,
                "created_at": logo.created_at.isoformat(),
            }
            for logo in recent
        ]
    }


@router.get("/tags")
async def get_all_tags(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all unique tags used by the current user"""
    result = await db.execute(
        select(LogoUpload.tags)
        .where(
            LogoUpload.user_id == user.id,
            LogoUpload.status == "active",
            LogoUpload.tags.isnot(None)
        )
    )
    
    # Collect all unique tags
    all_tags = set()
    for row in result.all():
        if row[0]:  # tags field
            all_tags.update(row[0])
    
    # Count usage of each tag
    tag_counts = {}
    for tag in all_tags:
        result = await db.execute(
            select(func.count())
            .select_from(LogoUpload)
            .where(
                LogoUpload.user_id == user.id,
                LogoUpload.status == "active",
                LogoUpload.tags.contains([tag])
            )
        )
        tag_counts[tag] = result.scalar()
    
    # Sort by usage count
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "tags": [
            {"tag": tag, "count": count}
            for tag, count in sorted_tags
        ]
    }
