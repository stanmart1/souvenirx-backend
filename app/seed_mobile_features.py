"""
Seed data for mobile app features
Product bundles, trending templates, and sample user projects
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import async_session
from app.models.product_bundle import ProductBundle
from app.models.trending_template import TrendingTemplate
from app.models.user_project import UserProject
from app.models.design_template import DesignTemplate
from app.models.product import Product
from app.models.user import User


async def seed_product_bundles(db: AsyncSession):
    """Seed product bundles"""
    print("Seeding product bundles...")
    
    # Check if bundles already exist
    result = await db.execute(select(ProductBundle).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        print("Product bundles already seeded")
        return
    
    bundles = [
        {
            'name': 'Summer Reunion Pack',
            'slug': 'summer-reunion-pack',
            'description': 'Perfect for summer reunions and gatherings',
            'tagline': 'Start from a tote, mug & thank-you card set.',
            'original_price': 3990,  # $39.90
            'discounted_price': 2490,  # $24.90
            'discount_percentage': 38,
            'product_ids': ['tote-bag', 'mug', 'thank-you-card'],
            'bundle_data': {
                'products': [
                    {'product_type': 'tote_bag', 'quantity': 1, 'variant': 'Navy Blue'},
                    {'product_type': 'mug', 'quantity': 1, 'variant': 'White'},
                    {'product_type': 'card', 'quantity': 1, 'variant': 'Cream'}
                ],
                'savings': 1500
            },
            'image_url': '/uploads/bundles/summer-reunion-pack.jpg',
            'thumbnail_url': '/uploads/bundles/summer-reunion-pack-thumb.jpg',
            'banner_images': [
                '/uploads/bundles/summer-reunion-1.jpg',
                '/uploads/bundles/summer-reunion-2.jpg',
                '/uploads/bundles/summer-reunion-3.jpg'
            ],
            'is_featured': True,
            'is_active': True,
            'display_order': 1,
            'delivery_time': '2-3 day delivery',
            'category': 'Events',
            'tags': ['reunion', 'summer', 'family', 'gifts'],
            'stock_status': 'in_stock',
            'view_count': 245,
            'purchase_count': 32,
            'popularity_score': 88.5
        },
        {
            'name': 'Corporate Branding Kit',
            'slug': 'corporate-branding-kit',
            'description': 'Complete branding kit for corporate events',
            'tagline': 'Tote bags, mugs, keychains & stickers for your team.',
            'original_price': 5990,
            'discounted_price': 4490,
            'discount_percentage': 25,
            'product_ids': ['tote-bag', 'mug', 'keychain', 'sticker'],
            'bundle_data': {
                'products': [
                    {'product_type': 'tote_bag', 'quantity': 2, 'variant': 'Navy Blue'},
                    {'product_type': 'mug', 'quantity': 2, 'variant': 'White'},
                    {'product_type': 'keychain', 'quantity': 5, 'variant': 'Wood'},
                    {'product_type': 'sticker', 'quantity': 10, 'variant': 'Vinyl'}
                ],
                'savings': 1500
            },
            'image_url': '/uploads/bundles/corporate-kit.jpg',
            'thumbnail_url': '/uploads/bundles/corporate-kit-thumb.jpg',
            'is_featured': True,
            'is_active': True,
            'display_order': 2,
            'delivery_time': '3-5 day delivery',
            'category': 'Corporate',
            'tags': ['corporate', 'branding', 'team', 'business'],
            'stock_status': 'in_stock',
            'view_count': 189,
            'purchase_count': 24,
            'popularity_score': 72.9
        },
        {
            'name': 'Wedding Favor Bundle',
            'slug': 'wedding-favor-bundle',
            'description': 'Elegant wedding favors for your special day',
            'tagline': 'Thank-you cards, keychains & custom stickers.',
            'original_price': 4490,
            'discounted_price': 3490,
            'discount_percentage': 22,
            'product_ids': ['thank-you-card', 'keychain', 'sticker'],
            'bundle_data': {
                'products': [
                    {'product_type': 'card', 'quantity': 20, 'variant': 'Cream'},
                    {'product_type': 'keychain', 'quantity': 20, 'variant': 'Wood'},
                    {'product_type': 'sticker', 'quantity': 50, 'variant': 'Vinyl'}
                ],
                'savings': 1000
            },
            'image_url': '/uploads/bundles/wedding-favor.jpg',
            'thumbnail_url': '/uploads/bundles/wedding-favor-thumb.jpg',
            'is_featured': True,
            'is_active': True,
            'display_order': 3,
            'delivery_time': '5-7 day delivery',
            'category': 'Weddings',
            'tags': ['wedding', 'favor', 'elegant', 'celebration'],
            'stock_status': 'in_stock',
            'view_count': 312,
            'purchase_count': 45,
            'popularity_score': 135.2
        },
        {
            'name': 'Birthday Party Pack',
            'slug': 'birthday-party-pack',
            'description': 'Fun party favors for birthday celebrations',
            'tagline': 'Tote bags, stickers & thank-you cards.',
            'original_price': 2990,
            'discounted_price': 1990,
            'discount_percentage': 33,
            'product_ids': ['tote-bag', 'sticker', 'thank-you-card'],
            'bundle_data': {
                'products': [
                    {'product_type': 'tote_bag', 'quantity': 5, 'variant': 'Mixed Colors'},
                    {'product_type': 'sticker', 'quantity': 20, 'variant': 'Vinyl'},
                    {'product_type': 'card', 'quantity': 10, 'variant': 'Colorful'}
                ],
                'savings': 1000
            },
            'image_url': '/uploads/bundles/birthday-pack.jpg',
            'thumbnail_url': '/uploads/bundles/birthday-pack-thumb.jpg',
            'is_featured': True,
            'is_active': True,
            'display_order': 4,
            'delivery_time': '2-3 day delivery',
            'category': 'Celebrations',
            'tags': ['birthday', 'party', 'fun', 'kids'],
            'stock_status': 'in_stock',
            'view_count': 156,
            'purchase_count': 28,
            'popularity_score': 71.6
        },
        {
            'name': 'Starter Design Kit',
            'slug': 'starter-design-kit',
            'description': 'Try everything with our starter kit',
            'tagline': 'One of each: tote, mug, card, keychain & sticker.',
            'original_price': 3490,
            'discounted_price': 2490,
            'discount_percentage': 29,
            'product_ids': ['tote-bag', 'mug', 'thank-you-card', 'keychain', 'sticker'],
            'bundle_data': {
                'products': [
                    {'product_type': 'tote_bag', 'quantity': 1},
                    {'product_type': 'mug', 'quantity': 1},
                    {'product_type': 'card', 'quantity': 1},
                    {'product_type': 'keychain', 'quantity': 1},
                    {'product_type': 'sticker', 'quantity': 1}
                ],
                'savings': 1000
            },
            'image_url': '/uploads/bundles/starter-kit.jpg',
            'thumbnail_url': '/uploads/bundles/starter-kit-thumb.jpg',
            'is_featured': True,
            'is_active': True,
            'display_order': 5,
            'delivery_time': '2-3 day delivery',
            'category': 'Starter',
            'tags': ['starter', 'variety', 'sample', 'trial'],
            'stock_status': 'in_stock',
            'view_count': 423,
            'purchase_count': 67,
            'popularity_score': 176.3
        }
    ]
    
    for bundle_data in bundles:
        bundle = ProductBundle(**bundle_data)
        db.add(bundle)
    
    await db.commit()
    print(f"✅ Seeded {len(bundles)} product bundles")


async def seed_trending_templates(db: AsyncSession):
    """Seed trending templates"""
    print("Seeding trending templates...")
    
    # Check if trending templates already exist
    result = await db.execute(select(TrendingTemplate).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        print("Trending templates already seeded")
        return
    
    # Get some design templates
    result = await db.execute(
        select(DesignTemplate).where(DesignTemplate.is_active == True).limit(10)
    )
    templates = result.scalars().all()
    
    if not templates:
        print("⚠️  No design templates found. Skipping trending templates seed.")
        return
    
    trending_data = []
    for idx, template in enumerate(templates):
        trending_data.append({
            'template_id': template.id,
            'display_name': template.name,
            'display_order': idx + 1,
            'trending_score': 100 - (idx * 10),
            'view_count_24h': 150 - (idx * 15),
            'usage_count_7d': 80 - (idx * 8),
            'is_active': True,
            'is_featured': idx < 4  # First 4 are featured
        })
    
    for data in trending_data:
        trending = TrendingTemplate(**data)
        db.add(trending)
    
    await db.commit()
    print(f"✅ Seeded {len(trending_data)} trending templates")


async def seed_sample_user_projects(db: AsyncSession):
    """Seed sample user projects for demo"""
    print("Seeding sample user projects...")
    
    # Get a user (preferably admin for demo)
    result = await db.execute(select(User).where(User.role.contains('admin')).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
    
    if not user:
        print("⚠️  No users found. Skipping user projects seed.")
        return
    
    # Check if projects already exist for this user
    result = await db.execute(select(UserProject).where(UserProject.user_id == user.id).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        print("Sample user projects already seeded")
        return
    
    # Get some templates and products
    result = await db.execute(select(DesignTemplate).limit(3))
    templates = result.scalars().all()
    result = await db.execute(select(Product).limit(3))
    products = result.scalars().all()
    
    if not templates or not products:
        print("⚠️  Not enough templates or products. Skipping user projects seed.")
        return
    
    projects = [
        {
            'user_id': user.id,
            'name': 'Family Picnic Pack',
            'description': 'Custom tote bags for family picnic',
            'status': 'in_progress',
            'template_id': templates[0].id if len(templates) > 0 else None,
            'product_id': products[0].id if len(products) > 0 else None,
            'project_data': {
                'product_type': 'tote_bag',
                'template_name': 'Classic Script',
                'customizations': {
                    'text': 'Good times Great people',
                    'color': 'Navy Blue',
                    'font': 'Script'
                },
                'progress': {
                    'step': 3,
                    'total_steps': 4,
                    'completed_steps': ['product', 'template', 'customize']
                }
            },
            'thumbnail_url': '/uploads/projects/family-picnic-thumb.jpg',
            'completion_percentage': 75,
            'current_step': 3,
            'total_steps': 4,
            'last_edited_at': datetime.now(timezone.utc) - timedelta(days=2)
        },
        {
            'user_id': user.id,
            'name': 'Bridal Shower Set',
            'description': 'Thank you cards for bridal shower',
            'status': 'completed',
            'template_id': templates[1].id if len(templates) > 1 else None,
            'product_id': products[1].id if len(products) > 1 else None,
            'project_data': {
                'product_type': 'card',
                'template_name': 'Elegant Serif',
                'customizations': {
                    'text': 'Thank you',
                    'color': 'Gold',
                    'font': 'Serif'
                }
            },
            'thumbnail_url': '/uploads/projects/bridal-shower-thumb.jpg',
            'completion_percentage': 100,
            'current_step': 4,
            'total_steps': 4,
            'last_edited_at': datetime.now(timezone.utc) - timedelta(days=5),
            'completed_at': datetime.now(timezone.utc) - timedelta(days=5)
        },
        {
            'user_id': user.id,
            'name': 'Team Building Mugs',
            'description': 'Custom mugs for team building event',
            'status': 'in_progress',
            'template_id': templates[2].id if len(templates) > 2 else None,
            'product_id': products[2].id if len(products) > 2 else None,
            'project_data': {
                'product_type': 'mug',
                'template_name': 'Bold & Fun',
                'customizations': {
                    'text': 'Team work',
                    'color': 'Black',
                    'font': 'Bold'
                },
                'progress': {
                    'step': 2,
                    'total_steps': 4,
                    'completed_steps': ['product', 'template']
                }
            },
            'thumbnail_url': '/uploads/projects/team-mugs-thumb.jpg',
            'completion_percentage': 50,
            'current_step': 2,
            'total_steps': 4,
            'last_edited_at': datetime.now(timezone.utc) - timedelta(hours=6)
        }
    ]
    
    for project_data in projects:
        project = UserProject(**project_data)
        db.add(project)
    
    await db.commit()
    print(f"✅ Seeded {len(projects)} sample user projects")


async def seed_mobile_features():
    """Main seed function for mobile features"""
    async with async_session() as db:
        try:
            await seed_product_bundles(db)
            await seed_trending_templates(db)
            await seed_sample_user_projects(db)
            print("✅ Mobile features seeding completed!")
        except Exception as e:
            print(f"❌ Error seeding mobile features: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(seed_mobile_features())
