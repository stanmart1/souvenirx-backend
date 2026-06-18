"""Public font catalogue endpoint used by the customisation flow."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.design_font import DesignFont

router = APIRouter(prefix="/api/fonts", tags=["Fonts"])


@router.get("")
async def list_fonts(
    category: str | None = Query(None),
    include_premium: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(DesignFont)
        .where(DesignFont.is_active == True)
        .order_by(DesignFont.sort_order.asc(), DesignFont.id.asc())
    )
    if category:
        stmt = stmt.where(DesignFont.category == category)
    if not include_premium:
        stmt = stmt.where(DesignFont.is_premium == False)

    result = await db.execute(stmt)
    fonts = result.scalars().all()

    return {
        "items": [
            {
                "id": f.id,
                "name": f.name,
                "display_name": f.display_name,
                "category": f.category,
                "source_type": f.source_type,
                "file_url": f.file_url,
                "preview_text": f.preview_text,
                "sample_image_url": f.sample_image_url,
                "is_premium": f.is_premium,
            }
            for f in fonts
        ]
    }
