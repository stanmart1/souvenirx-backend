"""Seed data for design templates"""

import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import async_session
from app.models.design_template import DesignTemplate
from app.models.user import User


# Sample design templates with complete design data
SAMPLE_TEMPLATES = [
    {
        "name": "Classic Script",
        "slug": "classic-script",
        "description": "Elegant script font with decorative flourishes. Perfect for weddings, anniversaries, and formal events.",
        "category": "Script & Calligraphy",
        "style": "elegant",
        "tags": ["wedding", "formal", "elegant", "script", "calligraphy"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": "#ffffff"
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "text",
                    "content": "Your Text Here",
                    "properties": {
                        "x": 500,
                        "y": 400,
                        "fontSize": 72,
                        "fontFamily": "Great Vibes",
                        "color": "#2c3e50",
                        "textAlign": "center",
                        "fontWeight": "normal",
                        "fontStyle": "normal",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-2",
                    "type": "shape",
                    "content": "decorative-line",
                    "properties": {
                        "x": 500,
                        "y": 500,
                        "width": 300,
                        "height": 2,
                        "color": "#d4af37",
                        "rotation": 0,
                        "opacity": 0.8
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/classic-script-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/classic-script-preview-1.jpg",
            "https://storage.souvenirx.com/templates/classic-script-preview-2.jpg"
        ],
        "compatible_products": [],  # Universal - works with all products
        "is_premium": False,
        "premium_price": 0,
        "is_featured": True,
    },
    {
        "name": "Bold & Fun",
        "slug": "bold-fun",
        "description": "Strong, contemporary design with bold typography. Ideal for corporate events and modern branding.",
        "category": "Modern & Minimalist",
        "style": "modern",
        "tags": ["corporate", "modern", "bold", "minimalist", "professional"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": "#1a1a1a"
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "text",
                    "content": "Team\nwork",
                    "properties": {
                        "x": 500,
                        "y": 450,
                        "fontSize": 96,
                        "fontFamily": "Montserrat",
                        "color": "#ffffff",
                        "textAlign": "center",
                        "fontWeight": "900",
                        "fontStyle": "normal",
                        "letterSpacing": 10,
                        "rotation": 0,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-2",
                    "type": "shape",
                    "content": "heart",
                    "properties": {
                        "x": 500,
                        "y": 600,
                        "size": 40,
                        "color": "#00ff88",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/bold-fun-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/bold-fun-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": False,
        "premium_price": 0,
        "is_featured": True,
    },
    {
        "name": "Elegant Serif",
        "slug": "elegant-serif",
        "description": "Classic vintage badge design with ornamental details. Great for retro-themed events and products.",
        "category": "Vintage & Retro",
        "style": "vintage",
        "tags": ["vintage", "retro", "badge", "classic", "ornamental"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": "#f4e8d8"
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "shape",
                    "content": "circle",
                    "properties": {
                        "x": 500,
                        "y": 500,
                        "radius": 300,
                        "strokeColor": "#8b4513",
                        "strokeWidth": 8,
                        "fillColor": "transparent",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-2",
                    "type": "text",
                    "content": "Made for\nmemories",
                    "properties": {
                        "x": 500,
                        "y": 440,
                        "fontSize": 72,
                        "fontFamily": "Cormorant Garamond",
                        "color": "#8b4513",
                        "textAlign": "center",
                        "fontWeight": "normal",
                        "fontStyle": "italic",
                        "letterSpacing": 2,
                        "rotation": 0,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-3",
                    "type": "shape",
                    "content": "heart",
                    "properties": {
                        "x": 500,
                        "y": 600,
                        "size": 40,
                        "color": "#8b4513",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/elegant-serif-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/elegant-serif-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": False,
        "premium_price": 0,
        "is_featured": True,
    },
    {
        "name": "Handwritten",
        "slug": "handwritten",
        "description": "Colorful and energetic design with playful elements. Perfect for kids' events and casual celebrations.",
        "category": "Fun & Playful",
        "style": "playful",
        "tags": ["kids", "fun", "colorful", "playful", "party"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": "#fff9e6"
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "text",
                    "content": "Adventure\nawaits",
                    "properties": {
                        "x": 500,
                        "y": 450,
                        "fontSize": 72,
                        "fontFamily": "Caveat",
                        "color": "#34495e",
                        "textAlign": "center",
                        "fontWeight": "700",
                        "rotation": -3,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-2",
                    "type": "shape",
                    "content": "heart",
                    "properties": {
                        "x": 500,
                        "y": 600,
                        "size": 40,
                        "color": "#ff6b6b",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/handwritten-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/handwritten-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": False,
        "premium_price": 0,
        "is_featured": True,
    },
]


async def seed_design_templates(db: AsyncSession | None = None):
    """Seed the database with sample design templates.

    When called without a session (e.g. as a standalone script) it opens its
    own. The main seed() passes its own session so everything runs inside a
    single transaction on startup.
    """
    owns_session = db is None
    if owns_session:
        ctx = async_session()
        session = await ctx.__aenter__()
    else:
        session = db
    try:
        # Get first admin user to set as creator
        from app.models.rbac import Role, user_roles
        result = await session.execute(
            select(User)
            .join(user_roles, User.id == user_roles.c.user_id)
            .join(Role, user_roles.c.role_id == Role.id)
            .where(Role.name == "admin")
            .limit(1)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            print("❌ No admin user found. Please create an admin user first.")
            return

        print(f"📝 Seeding design templates (created by: {admin.email})...")

        created_count = 0
        skipped_count = 0

        for template_data in SAMPLE_TEMPLATES:
            # Check if template already exists
            result = await session.execute(
                select(DesignTemplate).where(DesignTemplate.slug == template_data['slug'])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  ⏭️  Skipping '{template_data['name']}' (already exists)")
                skipped_count += 1
                continue

            # Create new template
            template = DesignTemplate(
                id=uuid.uuid4(),
                name=template_data['name'],
                slug=template_data['slug'],
                description=template_data['description'],
                category=template_data['category'],
                style=template_data['style'],
                tags=template_data['tags'],
                design_data=template_data['design_data'],
                thumbnail_url=template_data['thumbnail_url'],
                preview_images=template_data['preview_images'],
                compatible_products=template_data['compatible_products'],
                is_premium=template_data['is_premium'],
                premium_price=template_data['premium_price'],
                is_featured=template_data['is_featured'],
                created_by=admin.id,
                is_active=True,
                usage_count=0,
                popularity_score=0.0
            )

            session.add(template)
            created_count += 1
            print(f"  ✅ Created '{template_data['name']}'")

        if owns_session:
            await session.commit()

        print(f"\n✨ Design template seeding complete!")
        print(f"   Created: {created_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total: {len(SAMPLE_TEMPLATES)}")

    except Exception:
        if owns_session:
            await session.rollback()
        raise
    finally:
        if owns_session:
            await ctx.__aexit__(None, None, None)


async def main():
    """Main function to run the seeding"""
    await seed_design_templates()


if __name__ == "__main__":
    asyncio.run(main())
