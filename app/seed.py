"""Seed the database with initial data from the frontend data.ts."""
import asyncio
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, async_session, Base
from app.models import (
    User, Category, Product, ProductImage, ProductTier, ProductCustomization,
    Review, DeliveryZone, PromoCode, BankAccount, Settings, EmailTemplate, SmsTemplate,
)
from app.services.auth import hash_password


async def seed_email_and_sms_templates():
    """Upsert default email and SMS templates.  Safe to call on every startup —
    only inserts templates that don't already exist in the database."""
    from app.data.email_templates import DEFAULT_EMAIL_TEMPLATES
    from app.data.sms_templates import DEFAULT_SMS_TEMPLATES

    async with async_session() as db:
        inserted = 0

        # --- Email templates ---
        for t in DEFAULT_EMAIL_TEMPLATES:
            existing = await db.execute(select(EmailTemplate).where(EmailTemplate.name == t["name"]))
            if not existing.scalar_one_or_none():
                db.add(EmailTemplate(
                    name=t["name"],
                    subject=t["subject"],
                    html_content=t["html_content"],
                    variables=t["variables"],
                    is_active=t["is_active"],
                ))
                inserted += 1

        # --- SMS templates ---
        for name, text in DEFAULT_SMS_TEMPLATES.items():
            existing = await db.execute(select(SmsTemplate).where(SmsTemplate.name == name))
            if not existing.scalar_one_or_none():
                import re
                variables = {m: "string" for m in re.findall(r'\{(\w+)\}', text)}
                db.add(SmsTemplate(name=name, template=text, variables=variables, is_active=True))
                inserted += 1

        await db.commit()
        if inserted:
            print(f"[SEED] Inserted {inserted} missing email/SMS templates.")


async def seed():
    async with async_session() as db:
        # Check if already seeded
        result = await db.execute(select(Category))
        if result.scalars().first():
            print("Database already seeded, skipping.")
            return

        # --- Admin user ---
        admin = User(
            email="admin@souvenirx.com",
            password_hash=hash_password("admin123"),
            full_name="Admin User",
            phone="+234 800 000 0000",
            role="admin",
        )
        db.add(admin)

        # --- Demo customer ---
        customer = User(
            email="demo@souvenirx.com",
            password_hash=hash_password("demo123"),
            full_name="Demo Customer",
            phone="+234 801 234 5678",
            role="customer",
        )
        db.add(customer)
        await db.flush()

        # --- Categories ---
        categories_data = [
            # icon values are Lucide React icon component names rendered by the frontend
            ("mugs",       "Custom Mugs",      "Coffee",      1),
            ("tshirts",    "Branded T-Shirts",  "Shirt",       2),
            ("tote-bags",  "Tote Bags",         "ShoppingBag", 3),
            ("plaques",    "Engraved Plaques",  "Award",       4),
            ("cards",      "Greeting Cards",    "Mail",        5),
            ("wristbands", "Wristbands",        "Watch",       6),
            ("keychains",  "Keychains",         "Key",         7),
            ("stickers",   "Stickers",          "StickyNote",  8),
        ]
        cat_map = {}
        for slug, name, icon, sort in categories_data:
            cat = Category(slug=slug, name=name, icon=icon, sort_order=sort)
            db.add(cat)
            cat_map[slug] = cat
        await db.flush()

        # --- Products ---
        img = lambda seed, w=800: f"https://images.unsplash.com/{seed}?auto=format&fit=crop&w={w}&q=80"

        products_data = [
            {
                "slug": "custom-ceramic-mug", "name": "Custom Ceramic Mug", "category": "mugs",
                "description": "Premium 11oz ceramic mug with full-color print. Dishwasher safe, microwave friendly. Perfect for events, gifts, and corporate branding.",
                "base_price": 3500, "moq": 10, "stock": 480, "rating": 4.8, "reviews_count": 312,
                "tags": ["bestseller"],
                "images": [img("photo-1514228742587-6b1558fcca3d"), img("photo-1572119865084-43c285814d63"), img("photo-1577937927133-66ef06acdf18")],
                "tiers": [(10, 3500), (50, 2900), (100, 2400), (500, 1950)],
                "customizations": [
                    ("text", "Name / Event Text", 30, None),
                    ("option", "Color", None, ["White", "Black", "Gold rim"]),
                    ("logo", "Logo Upload", None, None),
                ],
            },
            {
                "slug": "branded-tshirt", "name": "Branded Cotton T-Shirt", "category": "tshirts",
                "description": "180gsm 100% cotton tee with DTF print. Available in sizes S-XXL. Vibrant prints that survive 50+ washes.",
                "base_price": 5200, "moq": 12, "stock": 620, "rating": 4.7, "reviews_count": 198,
                "tags": ["trending"],
                "images": [img("photo-1521572163474-6864f9cf17ab"), img("photo-1583743814966-8936f5b7be1a"), img("photo-1503341504253-dff4815485f1")],
                "tiers": [(12, 5200), (50, 4500), (100, 3900), (300, 3400)],
                "customizations": [
                    ("text", "Front Text", 25, None),
                    ("text", "Back Text", 25, None),
                    ("option", "Size", None, ["S", "M", "L", "XL", "XXL"]),
                    ("option", "Color", None, ["White", "Black", "Navy", "Maroon"]),
                    ("logo", "Logo Upload", None, None),
                ],
            },
            {
                "slug": "ankara-tote", "name": "Ankara Print Tote Bag", "category": "tote-bags",
                "description": "Handcrafted Ankara fabric tote with sturdy canvas lining. A statement piece for events and giveaways.",
                "base_price": 4200, "moq": 20, "stock": 230, "rating": 4.9, "reviews_count": 144,
                "tags": ["new"],
                "images": [img("photo-1591561954557-26941169b49e"), img("photo-1544816155-12df9643f363"), img("photo-1597481499750-3e6b22637e12")],
                "tiers": [(20, 4200), (50, 3700), (100, 3200)],
                "customizations": [
                    ("text", "Embroidered Name", 20, None),
                    ("option", "Pattern", None, ["Blue Wax", "Gold Royal", "Sunset"]),
                    ("logo", "Logo Upload", None, None),
                ],
            },
            {
                "slug": "wooden-plaque", "name": "Engraved Wooden Plaque", "category": "plaques",
                "description": "Solid mahogany plaque, laser engraved. Ideal for awards, recognitions, and corporate gifting.",
                "base_price": 12500, "moq": 5, "stock": 90, "rating": 5.0, "reviews_count": 76,
                "tags": ["premium"],
                "images": [img("photo-1607344645866-009c320b63e0"), img("photo-1606293459339-aa5d34a7b0e1"), img("photo-1582719478250-c89cae4dc85b")],
                "tiers": [(5, 12500), (20, 10500), (50, 8800)],
                "customizations": [
                    ("text", "Recipient Name", 40, None),
                    ("text", "Award Title", 50, None),
                    ("text", "Date", 15, None),
                    ("option", "Finish", None, ["Natural", "Walnut", "Mahogany"]),
                    ("logo", "Logo Upload", None, None),
                ],
            },
            {
                "slug": "wedding-thank-you-card", "name": "Gold Foil Thank-You Cards", "category": "cards",
                "description": "Luxurious gold-foil stamped cards on 350gsm matte paper with envelopes. Perfect for weddings & corporate.",
                "base_price": 850, "moq": 50, "stock": 1800, "rating": 4.9, "reviews_count": 421,
                "tags": ["bestseller"],
                "images": [img("photo-1607344645866-009c320b63e0"), img("photo-1606293459339-aa5d34a7b0e1"), img("photo-1582719478250-c89cae4dc85b")],
                "tiers": [(50, 850), (200, 700), (500, 580), (1000, 450)],
                "customizations": [
                    ("text", "Couple / Sender Names", 40, None),
                    ("text", "Event Date", 20, None),
                    ("option", "Foil Color", None, ["Gold", "Rose Gold", "Silver"]),
                ],
            },
            {
                "slug": "silicone-wristband", "name": "Silicone Wristbands", "category": "wristbands",
                "description": "Debossed silicone wristbands in any Pantone color. Quick turnaround for events and campaigns.",
                "base_price": 320, "moq": 100, "stock": 5200, "rating": 4.6, "reviews_count": 287,
                "tags": [],
                "images": [img("photo-1622445275576-721325763afe"), img("photo-1611601322175-ef8ec8c85f01"), img("photo-1610630844859-23c2c11c9aa6")],
                "tiers": [(100, 320), (500, 240), (1000, 180), (5000, 130)],
                "customizations": [
                    ("text", "Text on Band", 20, None),
                    ("option", "Color", None, ["Red", "Black", "Royal Blue", "Gold", "White"]),
                ],
            },
        ]

        product_objs = {}
        for pd in products_data:
            p = Product(
                slug=pd["slug"], name=pd["name"], category_id=cat_map[pd["category"]].id,
                description=pd["description"], base_price=pd["base_price"], moq=pd["moq"],
                stock=pd["stock"], rating=pd["rating"], reviews_count=pd["reviews_count"],
                tags=pd["tags"],
            )
            db.add(p)
            await db.flush()
            product_objs[pd["slug"]] = p

            for i, url in enumerate(pd["images"]):
                db.add(ProductImage(product_id=p.id, url=url, alt_text=pd["name"], sort_order=i))

            for min_qty, unit_price in pd["tiers"]:
                db.add(ProductTier(product_id=p.id, min_qty=min_qty, unit_price=unit_price))

            for ctype, label, max_len, values in pd["customizations"]:
                db.add(ProductCustomization(
                    product_id=p.id, type=ctype, label=label,
                    max_length=max_len, values=values,
                ))

        await db.flush()

        # --- Reviews ---
        reviews_data = [
            ("custom-ceramic-mug", "Adaeze O.", 5, "Amazing quality!", "Got 500 mugs in 4 days for our gala. Print quality was unreal — guests kept asking where we got them.", True, 24),
            ("custom-ceramic-mug", "Tunde A.", 5, "Perfect for corporate", "We use SouvenirX for all our onboarding gifts. Bulk pricing makes it a no-brainer.", True, 18),
            ("custom-ceramic-mug", "Bola E.", 4, "Great mugs, minor delay", "Mugs were fantastic. One batch had a slight color variation but the team replaced them quickly.", True, 7),
            ("branded-tshirt", "Kemi A.", 5, "Best tees we've ordered", "The print survived 50+ washes without fading. Our staff love them.", True, 31),
            ("branded-tshirt", "Yusuf B.", 4, "Good quality fabric", "180gsm cotton is really nice. Would love more color options though.", True, 12),
            ("ankara-tote", "Chioma N.", 5, "Wedding hit!", "The Ankara totes and gold cards were the talk of the wedding. Worth every naira.", True, 42),
            ("ankara-tote", "Fatima M.", 5, "Beautiful craftsmanship", "Each bag is unique due to the Ankara pattern. Our clients were impressed.", True, 15),
            ("wooden-plaque", "David O.", 5, "Premium quality", "The mahogany plaque looked absolutely stunning. Laser engraving was crisp and detailed.", True, 28),
            ("wooden-plaque", "Grace I.", 5, "Award-worthy", "Used these for our annual awards ceremony. Recipients were moved to tears.", True, 19),
            ("wedding-thank-you-card", "Amaka U.", 5, "Elegant cards", "The gold foil is stunning in person. Our wedding guests loved them.", True, 35),
            ("wedding-thank-you-card", "Emeka C.", 4, "Beautiful but pricey", "Quality is excellent. Wish the price was slightly lower for bulk orders.", True, 9),
            ("silicone-wristband", "Zainab M.", 5, "Fast turnaround", "Ordered 5000 wristbands for our campaign. Delivered in 3 days!", True, 22),
            ("silicone-wristband", "Obinna K.", 4, "Good for events", "Colors are vibrant. The debossing looks professional.", True, 11),
        ]
        slug_to_id = {s: p.id for s, p in product_objs.items()}
        for slug, author, rating, title, text, verified, helpful in reviews_data:
            db.add(Review(
                product_id=slug_to_id[slug], author=author, rating=rating,
                title=title, text=text, is_verified=verified, helpful_count=helpful,
            ))

        # --- Delivery Zones ---
        zones_data = [
            ("Lagos Mainland", 2500, 5000, "2–4 days"),
            ("Lagos Island / Lekki", 3500, 6500, "1–3 days"),
            ("Abuja", 4500, 8000, "3–5 days"),
            ("Port Harcourt", 5000, 9500, "3–6 days"),
            ("Other states", 6500, 12000, "5–8 days"),
        ]
        for name, std, exp, eta in zones_data:
            db.add(DeliveryZone(zone_name=name, standard_fee=std, express_fee=exp, eta_text=eta))

        # --- Promo Codes ---
        db.add(PromoCode(code="SAVE10", discount_percent=10, min_order_amount=0, is_active=True))
        db.add(PromoCode(code="WELCOME15", discount_percent=15, min_order_amount=50000, is_active=True))

        # --- Bank Accounts ---
        db.add(BankAccount(bank_name="Guaranty Trust Bank (GTB)", account_name="SouvenirX Ltd", account_number="0123456789", sort_order=1))
        db.add(BankAccount(bank_name="Access Bank", account_name="SouvenirX Ltd", account_number="9876543210", sort_order=2))

        # --- Settings ---
        db.add(Settings(key="ga_id", value={"value": ""}))
        db.add(Settings(key="fb_pixel_id", value={"value": ""}))
        db.add(Settings(key="seo_title", value={"value": "SouvenirX — Custom Souvenirs"}))
        db.add(Settings(key="seo_description", value={"value": "Design custom mugs, t-shirts, plaques and event souvenirs in bulk."}))
        db.add(Settings(key="affiliate_commission_rate", value={"value": 0.10}))
        db.add(Settings(key="affiliate_cookie_days", value={"value": 30}))
        db.add(Settings(key="free_shipping_threshold", value={"value": 150000}))

        await db.commit()
        print("Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
