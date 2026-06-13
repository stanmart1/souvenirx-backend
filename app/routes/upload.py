import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.logo_upload import LogoUpload, LogoUploadStatus
from app.models.order import Order
from app.models.product import Product
from app.redis import check_rate_limit

router = APIRouter()

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/svg+xml", "application/pdf"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB

# Logo upload configuration
LOGO_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOGO_ALLOWED_MIME_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/webp"]
LOGO_UPLOAD_DIR = "uploads/logos"


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if not await check_rate_limit(f"rl:upload:{user.id}", 20, 60):
        raise HTTPException(status_code=429, detail="Too many uploads. Please wait.")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    ext = file.filename.split(".")[-1] if file.filename else "png"
    filename = f"{uuid.uuid4()}.{ext}"
    upload_path = Path(settings.upload_dir) / "products" / filename
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    with open(upload_path, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/products/{filename}", "filename": filename}


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def _generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension."""
    ext = os.path.splitext(original_filename)[1]
    return f"{uuid.uuid4().hex}{ext}"


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    product_id: str = Form(None),
    order_id: str = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo file for product customization.
    
    The logo can be associated with:
    - A specific product (for pre-order customization)
    - A specific order (for post-order customization)
    - Just the user (for general use)
    """
    # Validate file size
    file_content = await file.read()
    if len(file_content) > LOGO_MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {LOGO_MAX_SIZE // (1024*1024)}MB limit")
    
    # Validate MIME type
    if file.content_type not in LOGO_ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(LOGO_ALLOWED_MIME_TYPES)}"
        )
    
    # Validate associations
    if product_id:
        try:
            product_uuid = uuid.UUID(product_id)
            result = await db.execute(select(Product).where(Product.id == product_uuid))
            if not result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Product not found")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid product ID")
    
    if order_id:
        try:
            order_uuid = uuid.UUID(order_id)
            result = await db.execute(select(Order).where(Order.id == order_uuid))
            if not result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Order not found")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid order ID")
    
    # Generate unique filename
    unique_filename = _generate_unique_filename(file.filename)
    upload_path = Path(settings.upload_dir) / LOGO_UPLOAD_DIR / unique_filename
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save file
    with open(upload_path, "wb") as f:
        f.write(file_content)
    
    # In production, you would upload to S3/Cloudinary here and get a public URL
    # For now, we'll use a relative path that can be served
    file_url = f"/uploads/{LOGO_UPLOAD_DIR}/{unique_filename}"
    
    # Create database record
    logo_upload = LogoUpload(
        user_id=user.id,
        product_id=uuid.UUID(product_id) if product_id else None,
        order_id=uuid.UUID(order_id) if order_id else None,
        file_name=file.filename,
        file_url=file_url,
        file_size=_format_file_size(len(file_content)),
        mime_type=file.content_type,
        status=LogoUploadStatus.pending,
    )
    
    db.add(logo_upload)
    await db.flush()
    
    return {
        "id": str(logo_upload.id),
        "file_url": file_url,
        "file_name": file.filename,
        "file_size": logo_upload.file_size,
        "status": logo_upload.status,
        "message": "Logo uploaded successfully. Pending admin approval."
    }


@router.get("/logo/my-uploads")
async def list_my_uploads(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all logo uploads for the current user."""
    result = await db.execute(
        select(LogoUpload)
        .where(LogoUpload.user_id == user.id)
        .order_by(LogoUpload.created_at.desc())
    )
    uploads = result.scalars().all()
    
    return [
        {
            "id": str(upload.id),
            "file_url": upload.file_url,
            "file_name": upload.file_name,
            "file_size": upload.file_size,
            "status": upload.status,
            "rejection_reason": upload.rejection_reason,
            "created_at": upload.created_at.isoformat(),
        }
        for upload in uploads
    ]


@router.delete("/logo/{upload_id}")
async def delete_logo(
    upload_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a logo upload (only if pending or rejected)."""
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    
    result = await db.execute(
        select(LogoUpload).where(
            LogoUpload.id == upload_uuid,
            LogoUpload.user_id == user.id
        )
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    if upload.status == LogoUploadStatus.approved:
        raise HTTPException(status_code=400, detail="Cannot delete approved logos")
    
    # Delete file from disk
    try:
        file_path = upload.file_url.replace(f"/uploads/{LOGO_UPLOAD_DIR}/", str(Path(settings.upload_dir) / LOGO_UPLOAD_DIR / ""))
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass  # Continue even if file deletion fails
    
    await db.delete(upload)
    await db.flush()
    
    return {"message": "Logo deleted successfully"}


# Admin endpoints for logo management
@router.get("/admin/logo/pending")
async def list_pending_logos(
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all pending logo uploads for admin review."""
    result = await db.execute(
        select(LogoUpload)
        .where(LogoUpload.status == LogoUploadStatus.pending)
        .options(selectinload(LogoUpload.user))
        .order_by(LogoUpload.created_at.desc())
    )
    uploads = result.scalars().all()
    
    return [
        {
            "id": str(upload.id),
            "file_url": upload.file_url,
            "file_name": upload.file_name,
            "file_size": upload.file_size,
            "mime_type": upload.mime_type,
            "user_email": upload.user.email if upload.user else "Unknown",
            "user_name": upload.user.full_name if upload.user else "Unknown",
            "product_id": str(upload.product_id) if upload.product_id else None,
            "order_id": str(upload.order_id) if upload.order_id else None,
            "created_at": upload.created_at.isoformat(),
        }
        for upload in uploads
    ]


@router.post("/admin/logo/{upload_id}/approve")
async def approve_logo(
    upload_id: str,
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a logo upload."""
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    
    result = await db.execute(
        select(LogoUpload).where(LogoUpload.id == upload_uuid)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    upload.status = LogoUploadStatus.approved
    upload.reviewed_by = admin.id
    upload.reviewed_at = datetime.now(timezone.utc)
    
    await db.flush()
    
    return {"message": "Logo approved successfully"}


@router.post("/admin/logo/{upload_id}/reject")
async def reject_logo(
    upload_id: str,
    reason: str = Form(...),
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a logo upload with a reason."""
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    
    result = await db.execute(
        select(LogoUpload).where(LogoUpload.id == upload_uuid)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    upload.status = LogoUploadStatus.rejected
    upload.rejection_reason = reason
    upload.reviewed_by = admin.id
    upload.reviewed_at = datetime.now(timezone.utc)
    
    await db.flush()
    
    return {"message": "Logo rejected successfully"}
