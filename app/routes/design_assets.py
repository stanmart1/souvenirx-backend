"""Admin design asset library endpoints."""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.user import User

router = APIRouter(prefix="/api/design-assets", tags=["design-assets"])

ALLOWED_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/svg+xml",
    "image/webp",
}
MAX_SIZE = 5 * 1024 * 1024


@router.get("")
async def list_design_assets(
    category: Optional[str] = None,
    admin: User = Depends(get_current_admin),
):
    """List uploaded design assets (shapes, backgrounds, icons)."""
    assets_dir = Path(settings.upload_dir) / "design_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    items = []
    for path in assets_dir.iterdir():
        if not path.is_file():
            continue
        if category and not path.name.startswith(f"{category}_"):
            continue
        items.append({
            "id": path.name,
            "name": path.name,
            "url": f"/uploads/design_assets/{path.name}",
            "category": _category_from_filename(path.name),
        })

    return {"items": sorted(items, key=lambda x: x["name"])}


@router.post("")
async def upload_design_asset(
    file: UploadFile = File(...),
    category: str = "shapes",
    admin: User = Depends(get_current_admin),
):
    """Upload a design asset (shape, icon, background)."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed"
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    ext = file.filename.split(".")[-1] if file.filename else "png"
    safe_category = "".join(c if c.isalnum() else "_" for c in category)
    filename = f"{safe_category}_{uuid.uuid4().hex}.{ext}"

    upload_dir = Path(settings.upload_dir) / "design_assets"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "url": f"/uploads/design_assets/{filename}",
        "filename": filename,
        "category": category,
    }


def _category_from_filename(filename: str) -> str:
    """Extract category prefix from filename."""
    parts = filename.split("_")
    return parts[0] if parts else "shapes"
