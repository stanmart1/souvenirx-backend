"""System settings service for managing application-wide configuration"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import SystemSettings


async def get_setting(db: AsyncSession, key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a system setting by key"""
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else default


async def get_bool_setting(db: AsyncSession, key: str, default: bool = False) -> bool:
    """Get a boolean system setting"""
    value = await get_setting(db, key, str(default).lower())
    return value.lower() == "true" if value else default


async def get_int_setting(db: AsyncSession, key: str, default: int = 0) -> int:
    """Get an integer system setting"""
    value = await get_setting(db, key, str(default))
    try:
        return int(value) if value else default
    except ValueError:
        return default


async def get_float_setting(db: AsyncSession, key: str, default: float = 0.0) -> float:
    """Get a float system setting"""
    value = await get_setting(db, key, str(default))
    try:
        return float(value) if value else default
    except ValueError:
        return default


async def set_setting(db: AsyncSession, key: str, value: str, description: Optional[str] = None) -> None:
    """Set or update a system setting"""
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = SystemSettings(key=key, value=value, description=description)
        db.add(setting)
    
    await db.commit()
