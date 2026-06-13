"""Admin settings management"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.middleware.auth import get_current_admin as require_admin
from app.models.user import User
from app.models.settings import SystemSettings
from app.services.settings import get_setting, set_setting


router = APIRouter()


class UpdateSettingRequest(BaseModel):
    value: str


@router.get("/settings")
async def list_settings(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all system settings"""
    result = await db.execute(select(SystemSettings))
    settings = result.scalars().all()
    
    return [
        {
            "key": s.key,
            "value": s.value,
            "description": s.description,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in settings
    ]


@router.get("/settings/{key}")
async def get_setting_by_key(
    key: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific setting"""
    value = await get_setting(db, key)
    if value is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    setting = result.scalar_one_or_none()
    
    return {
        "key": key,
        "value": value,
        "description": setting.description if setting else None,
    }


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    req: UpdateSettingRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a system setting"""
    await set_setting(db, key, req.value)
    return {"message": "Setting updated successfully"}


@router.post("/settings/{key}")
async def create_setting(
    key: str,
    req: UpdateSettingRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new system setting"""
    existing = await get_setting(db, key)
    if existing:
        raise HTTPException(status_code=400, detail="Setting already exists")
    
    await set_setting(db, key, req.value)
    return {"message": "Setting created successfully"}
