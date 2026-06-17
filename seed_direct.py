"""
Direct seed script using asyncpg without SQLAlchemy SSL issues
"""
import asyncio
import asyncpg
from datetime import datetime, timezone, timedelta
import uuid

async def seed_bundles(conn):
    """Seed product bundles"""
    print("Seeding product bundles...")
    
    # Check if already seeded
    count = await conn.fetchval('SELECT COUNT(*) FROM product_bundles')
    if count > 0:
        print(f"  Already have {count} bundles, skipping...")
        return
    
    bundles = [
        ('Summer Reunion Pack', 'summer-reunion-pack', 'Perfect for summer reunions and gatherings', 
         'Start from a tote, mug & thank-you card set.', 3990, 2490, 38, 
         ['tote-bag', 'mug', 'thank-you-card'], '/uploads/bundles/summer-reunion-pack.jpg',
         True, True, 1, '2-3 day delivery', 'Events', ['reunion', 'summer', 'family', 'gifts'],
         'in_stock', 245, 32, 88.5),
        
        ('Corporate Branding Kit', 'corporate-branding-kit', 'Complete branding kit for corporate events',
         'Tote bags, mugs, keychains & stickers for your team.', 5990, 4490, 25,
         ['tote-bag', 'mug', 'keychain', 'sticker'], '/uploads/bundles/corporate-kit.jpg',
         True, True, 2, '3-5 day delivery', 'Corporate', ['corporate', 'branding', 'team', 'business'],
         'in_stock', 189, 24, 72.9),
        
        ('Wedding Favor Bundle', 'wedding-favor-bundle', 'Elegant wedding favors for your special day',
         'Thank-you cards, keychains & custom stickers.', 4490, 3490, 22,
         ['thank-you-card', 'keychain', 'sticker'], '/uploads/bundles/wedding-favor.jpg',
         True, True, 3, '5-7 day delivery', 'Weddings', ['wedding', 'favor', 'elegant', 'celebration'],
         'in_stock', 312, 45, 135.2),
        
        ('Birthday Party Pack', 'birthday-party-pack', 'Fun party favors for birthday celebrations',
         'Tote bags, stickers & thank-you cards.', 2990, 1990, 33,
         ['tote-bag', 'sticker', 'thank-you-card'], '/uploads/bundles/birthday-pack.jpg',
         True, True, 4, '2-3 day delivery', 'Celebrations', ['birthday', 'party', 'fun', 'kids'],
         'in_stock', 156, 28, 71.6),
        
        ('Starter Design Kit', 'starter-design-kit', 'Try everything with our starter kit',
         'One of each: tote, mug, card, keychain & sticker.', 3490, 2490, 29,
         ['tote-bag', 'mug', 'thank-you-card', 'keychain', 'sticker'], '/uploads/bundles/starter-kit.jpg',
         True, True, 5, '2-3 day delivery', 'Starter', ['starter', 'variety', 'sample', 'trial'],
         'in_stock', 423, 67, 176.3),
    ]
    
    for bundle in bundles:
        await conn.execute('''
            INSERT INTO product_bundles 
            (id, name, slug, description, tagline, original_price, discounted_price, discount_percentage,
             product_ids, image_url, is_featured, is_active, display_order, delivery_time, category, tags,
             stock_status, view_count, purchase_count, popularity_score, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
        ''', uuid.uuid4(), *bundle, datetime.now(timezone.utc), datetime.now(timezone.utc))
    
    print(f"✅ Seeded {len(bundles)} product bundles")


async def seed_trending(conn):
    """Seed trending templates"""
    print("Seeding trending templates...")
    
    # Check if already seeded
    count = await conn.fetchval('SELECT COUNT(*) FROM trending_templates')
    if count > 0:
        print(f"  Already have {count} trending templates, skipping...")
        return
    
    # Get some design templates
    templates = await conn.fetch('SELECT id, name FROM design_templates WHERE is_active = true LIMIT 10')
    
    if not templates:
        print("⚠️  No design templates found, skipping...")
        return
    
    for idx, template in enumerate(templates):
        await conn.execute('''
            INSERT INTO trending_templates
            (id, template_id, display_name, display_order, trending_score, view_count_24h, usage_count_7d,
             is_active, is_featured, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ''', uuid.uuid4(), template['id'], template['name'], idx + 1,
            100 - (idx * 10), 150 - (idx * 15), 80 - (idx * 8),
            True, idx < 4, datetime.now(timezone.utc), datetime.now(timezone.utc))
    
    print(f"✅ Seeded {len(templates)} trending templates")


async def seed_projects(conn):
    """Seed sample user projects"""
    print("Seeding sample user projects...")
    
    # Get a user
    user = await conn.fetchrow("SELECT id FROM users WHERE role LIKE '%admin%' LIMIT 1")
    if not user:
        user = await conn.fetchrow("SELECT id FROM users LIMIT 1")
    
    if not user:
        print("⚠️  No users found, skipping...")
        return
    
    # Check if already seeded
    count = await conn.fetchval('SELECT COUNT(*) FROM user_projects WHERE user_id = $1', user['id'])
    if count > 0:
        print(f"  Already have {count} projects for this user, skipping...")
        return
    
    # Get templates and products
    templates = await conn.fetch('SELECT id FROM design_templates LIMIT 3')
    products = await conn.fetch('SELECT id FROM products LIMIT 3')
    
    if not templates or not products:
        print("⚠️  Not enough templates or products, skipping...")
        return
    
    projects = [
        ('Family Picnic Pack', 'Custom tote bags for family picnic', 'in_progress',
         templates[0]['id'] if len(templates) > 0 else None, products[0]['id'] if len(products) > 0 else None,
         75, 3, 4, datetime.now(timezone.utc) - timedelta(days=2)),
        
        ('Bridal Shower Set', 'Thank you cards for bridal shower', 'completed',
         templates[1]['id'] if len(templates) > 1 else None, products[1]['id'] if len(products) > 1 else None,
         100, 4, 4, datetime.now(timezone.utc) - timedelta(days=5)),
        
        ('Team Building Mugs', 'Custom mugs for team building event', 'in_progress',
         templates[2]['id'] if len(templates) > 2 else None, products[2]['id'] if len(products) > 2 else None,
         50, 2, 4, datetime.now(timezone.utc) - timedelta(hours=6)),
    ]
    
    for project in projects:
        await conn.execute('''
            INSERT INTO user_projects
            (id, user_id, name, description, status, template_id, product_id,
             completion_percentage, current_step, total_steps, last_edited_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ''', uuid.uuid4(), user['id'], *project, datetime.now(timezone.utc), datetime.now(timezone.utc))
    
    print(f"✅ Seeded {len(projects)} sample user projects")


async def main():
    """Main seed function"""
    print("🌱 Starting seed process...")
    
    conn = await asyncpg.connect(
        host='149.102.159.118',
        port=54324,
        user='postgres',
        password='9EcBh1yYeCtyCLy2pcMrivIo7Z2U1y0Nd89BaGYI35B5gmBXDvUzulOyz4EbgiKF',
        database='postgres',
        ssl='disable'
    )
    
    try:
        await seed_bundles(conn)
        await seed_trending(conn)
        await seed_projects(conn)
        print("\n✅ All seed data completed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
