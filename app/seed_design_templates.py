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
        "name": "Bold & Modern",
        "slug": "bold-modern",
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
                    "content": "YOUR BRAND",
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
                    "content": "rectangle",
                    "properties": {
                        "x": 200,
                        "y": 550,
                        "width": 600,
                        "height": 8,
                        "color": "#00ff88",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/bold-modern-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/bold-modern-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": False,
        "premium_price": 0,
        "is_featured": True,
    },
    {
        "name": "Vintage Badge",
        "slug": "vintage-badge",
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
                    "content": "ESTABLISHED",
                    "properties": {
                        "x": 500,
                        "y": 400,
                        "fontSize": 24,
                        "fontFamily": "Bebas Neue",
                        "color": "#8b4513",
                        "textAlign": "center",
                        "fontWeight": "normal",
                        "letterSpacing": 5,
                        "rotation": 0,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-3",
                    "type": "text",
                    "content": "2024",
                    "properties": {
                        "x": 500,
                        "y": 500,
                        "fontSize": 120,
                        "fontFamily": "Bebas Neue",
                        "color": "#8b4513",
                        "textAlign": "center",
                        "fontWeight": "bold",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/vintage-badge-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/vintage-badge-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": False,
        "premium_price": 0,
        "is_featured": False,
    },
    {
        "name": "Playful Fun",
        "slug": "playful-fun",
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
                    "content": "Let's Party!",
                    "properties": {
                        "x": 500,
                        "y": 500,
                        "fontSize": 84,
                        "fontFamily": "Fredoka One",
                        "color": "#ff6b6b",
                        "textAlign": "center",
                        "fontWeight": "normal",
                        "rotation": -5,
                        "opacity": 1.0,
                        "shadow": {
                            "offsetX": 4,
                            "offsetY": 4,
                            "blur": 0,
                            "color": "#4ecdc4"
                        }
                    }
                },
                {
                    "id": "layer-2",
                    "type": "shape",
                    "content": "star",
                    "properties": {
                        "x": 200,
                        "y": 300,
                        "size": 60,
                        "color": "#ffd93d",
                        "rotation": 15,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-3",
                    "type": "shape",
                    "content": "star",
                    "properties": {
                        "x": 800,
                        "y": 350,
                        "size": 50,
                        "color": "#4ecdc4",
                        "rotation": -20,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/playful-fun-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/playful-fun-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": False,
        "premium_price": 0,
        "is_featured": False,
    },
    {
        "name": "Minimalist Monogram",
        "slug": "minimalist-monogram",
        "description": "Clean and sophisticated monogram design. Ideal for personal branding and elegant gifts.",
        "category": "Modern & Minimalist",
        "style": "minimalist",
        "tags": ["minimalist", "monogram", "elegant", "simple", "professional"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": "#ffffff"
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "shape",
                    "content": "circle",
                    "properties": {
                        "x": 500,
                        "y": 500,
                        "radius": 200,
                        "strokeColor": "#2c3e50",
                        "strokeWidth": 2,
                        "fillColor": "transparent",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-2",
                    "type": "text",
                    "content": "AB",
                    "properties": {
                        "x": 500,
                        "y": 520,
                        "fontSize": 120,
                        "fontFamily": "Playfair Display",
                        "color": "#2c3e50",
                        "textAlign": "center",
                        "fontWeight": "normal",
                        "fontStyle": "italic",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/minimalist-monogram-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/minimalist-monogram-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": True,
        "premium_price": 50000,  # 500 Naira in kobo
        "is_featured": True,
    },
    {
        "name": "Floral Elegance",
        "slug": "floral-elegance",
        "description": "Beautiful floral design with delicate botanical elements. Perfect for weddings and garden parties.",
        "category": "Nature & Floral",
        "style": "elegant",
        "tags": ["floral", "botanical", "wedding", "garden", "elegant"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": "#faf8f3"
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "text",
                    "content": "Your Event",
                    "properties": {
                        "x": 500,
                        "y": 500,
                        "fontSize": 64,
                        "fontFamily": "Cormorant Garamond",
                        "color": "#5a7c5a",
                        "textAlign": "center",
                        "fontWeight": "300",
                        "fontStyle": "italic",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-2",
                    "type": "image",
                    "content": "floral-corner",
                    "properties": {
                        "x": 100,
                        "y": 100,
                        "width": 200,
                        "height": 200,
                        "rotation": 0,
                        "opacity": 0.6
                    }
                },
                {
                    "id": "layer-3",
                    "type": "image",
                    "content": "floral-corner",
                    "properties": {
                        "x": 900,
                        "y": 900,
                        "width": 200,
                        "height": 200,
                        "rotation": 180,
                        "opacity": 0.6
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/floral-elegance-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/floral-elegance-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": True,
        "premium_price": 50000,
        "is_featured": True,
    },
    {
        "name": "Tech Gradient",
        "slug": "tech-gradient",
        "description": "Modern gradient design with tech-inspired aesthetics. Great for tech events and startups.",
        "category": "Modern & Minimalist",
        "style": "modern",
        "tags": ["tech", "gradient", "modern", "startup", "digital"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": {
                    "type": "gradient",
                    "colors": ["#667eea", "#764ba2"],
                    "angle": 135
                }
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "text",
                    "content": "INNOVATE",
                    "properties": {
                        "x": 500,
                        "y": 500,
                        "fontSize": 88,
                        "fontFamily": "Poppins",
                        "color": "#ffffff",
                        "textAlign": "center",
                        "fontWeight": "700",
                        "letterSpacing": 8,
                        "rotation": 0,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/tech-gradient-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/tech-gradient-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": False,
        "premium_price": 0,
        "is_featured": False,
    },
    {
        "name": "Rustic Charm",
        "slug": "rustic-charm",
        "description": "Warm rustic design with natural textures. Perfect for country-themed events and outdoor celebrations.",
        "category": "Vintage & Retro",
        "style": "rustic",
        "tags": ["rustic", "country", "natural", "outdoor", "warm"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": "#d4a574"
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "text",
                    "content": "Gather & Celebrate",
                    "properties": {
                        "x": 500,
                        "y": 500,
                        "fontSize": 56,
                        "fontFamily": "Amatic SC",
                        "color": "#3d2817",
                        "textAlign": "center",
                        "fontWeight": "700",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                },
                {
                    "id": "layer-2",
                    "type": "shape",
                    "content": "rectangle",
                    "properties": {
                        "x": 300,
                        "y": 580,
                        "width": 400,
                        "height": 3,
                        "color": "#3d2817",
                        "rotation": 0,
                        "opacity": 0.5
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/rustic-charm-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/rustic-charm-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": False,
        "premium_price": 0,
        "is_featured": False,
    },
    {
        "name": "Geometric Modern",
        "slug": "geometric-modern",
        "description": "Contemporary geometric patterns with clean lines. Ideal for modern events and corporate branding.",
        "category": "Modern & Minimalist",
        "style": "geometric",
        "tags": ["geometric", "modern", "abstract", "contemporary", "professional"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": "#ecf0f1"
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "shape",
                    "content": "triangle",
                    "properties": {
                        "x": 300,
                        "y": 400,
                        "size": 150,
                        "color": "#3498db",
                        "rotation": 0,
                        "opacity": 0.8
                    }
                },
                {
                    "id": "layer-2",
                    "type": "shape",
                    "content": "triangle",
                    "properties": {
                        "x": 700,
                        "y": 400,
                        "size": 150,
                        "color": "#e74c3c",
                        "rotation": 180,
                        "opacity": 0.8
                    }
                },
                {
                    "id": "layer-3",
                    "type": "text",
                    "content": "YOUR TEXT",
                    "properties": {
                        "x": 500,
                        "y": 600,
                        "fontSize": 64,
                        "fontFamily": "Raleway",
                        "color": "#2c3e50",
                        "textAlign": "center",
                        "fontWeight": "600",
                        "letterSpacing": 4,
                        "rotation": 0,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/geometric-modern-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/geometric-modern-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": True,
        "premium_price": 50000,
        "is_featured": False,
    },
    {
        "name": "Handwritten Note",
        "slug": "handwritten-note",
        "description": "Personal handwritten style design. Perfect for thank you notes and personal messages.",
        "category": "Script & Calligraphy",
        "style": "casual",
        "tags": ["handwritten", "personal", "casual", "note", "message"],
        "design_data": {
            "canvas": {
                "width": 1000,
                "height": 1000,
                "background": "#fffef7"
            },
            "layers": [
                {
                    "id": "layer-1",
                    "type": "text",
                    "content": "Thank You!",
                    "properties": {
                        "x": 500,
                        "y": 500,
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
                        "color": "#e74c3c",
                        "rotation": 0,
                        "opacity": 1.0
                    }
                }
            ]
        },
        "thumbnail_url": "https://storage.souvenirx.com/templates/handwritten-note-thumb.jpg",
        "preview_images": [
            "https://storage.souvenirx.com/templates/handwritten-note-preview-1.jpg"
        ],
        "compatible_products": [],
        "is_premium": False,
        "premium_price": 0,
        "is_featured": False,
    }
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
        result = await session.execute(
            select(User).where(User.role == "admin").limit(1)
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
