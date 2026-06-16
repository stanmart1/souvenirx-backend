from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.middleware.security import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import settings as cfg
    if cfg.jwt_secret == "change-me-to-a-random-secret-key":
        import logging
        logging.getLogger("souvenirx").warning(
            "JWT_SECRET is using the default value. Set JWT_SECRET in your environment for production!"
        )

    # Run seed (tables are created by Alembic migrations via start.sh)
    from app.seed import seed, seed_email_and_sms_templates
    await seed()
    # Ensure all default email/SMS templates exist in the database.
    # This is idempotent — safe to run on every startup.
    await seed_email_and_sms_templates()

    yield


app = FastAPI(title="SouvenirX API", version="1.0.0", lifespan=lifespan)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "https://souvenir-x.com",
        "https://www.souvenir-x.com",
        "https://api.souvenir-x.com",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    # Mobile apps don't send Origin header, so we need to allow requests without Origin
    # This is safe because mobile apps use JWT tokens for authentication
    allow_origin_regex=r".*",  # Allow all origins (mobile apps + web)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Allow mobile apps to read all response headers
)

# Serve uploaded files
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Import and include routers
from app.routes.auth import router as auth_router
from app.routes.products import router as products_router
from app.routes.cart import router as cart_router
from app.routes.wishlist import router as wishlist_router
from app.routes.orders import router as orders_router
from app.routes.payments import router as payments_router
from app.routes.delivery import router as delivery_router
from app.routes.promos import router as promos_router
from app.routes.affiliates import router as affiliates_router
from app.routes.reviews import router as reviews_router
from app.routes.upload import router as upload_router
from app.routes.notifications import router as notifications_router
from app.routes.support import router as support_router
from app.routes.testimonials import router as testimonials_router
from app.routes.newsletter import router as newsletter_router
from app.routes.payment_methods import router as payment_methods_router
from app.routes.admin import router as admin_router
from app.routes.email_templates import router as email_templates_router
from app.routes.admin_settings import router as admin_settings_router
from app.routes.stock_notifications import router as stock_notifications_router
from app.routes.campaigns import router as campaigns_router
from app.routes.auth_oauth import router as oauth_router
from app.routes.config import router as config_router
from app.routes.design_templates import router as design_templates_router
from app.routes.logos import router as logos_router
from app.routes.customer_designs import router as customer_designs_router
from app.routes.mockup_templates import router as mockup_templates_router
from app.routers.product_bundles import router as product_bundles_router
from app.routers.user_projects import router as user_projects_router
from app.routers.trending_templates import router as trending_templates_router
from app.routers.recommendations import router as recommendations_router

app.include_router(config_router, prefix="/api", tags=["Config"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(products_router, prefix="/api/products", tags=["Products"])
app.include_router(cart_router, prefix="/api/cart", tags=["Cart"])
app.include_router(wishlist_router, prefix="/api/wishlist", tags=["Wishlist"])
app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(payments_router, prefix="/api/payments", tags=["Payments"])
app.include_router(delivery_router, prefix="/api/delivery-zones", tags=["Delivery"])
app.include_router(promos_router, prefix="/api/promos", tags=["Promos"])
app.include_router(affiliates_router, prefix="/api/affiliates", tags=["Affiliates"])
app.include_router(reviews_router, prefix="/api/reviews", tags=["Reviews"])
app.include_router(upload_router, prefix="/api/upload", tags=["Upload"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(support_router, prefix="/api/support", tags=["Support"])
app.include_router(testimonials_router, prefix="/api/testimonials", tags=["Testimonials"])
app.include_router(newsletter_router, prefix="/api/newsletter", tags=["Newsletter"])
app.include_router(payment_methods_router, prefix="/api/payment-methods", tags=["Payment Methods"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(email_templates_router, prefix="/api/admin", tags=["Admin"])
app.include_router(admin_settings_router, prefix="/api/admin", tags=["Admin"])
app.include_router(stock_notifications_router, prefix="/api/stock-notifications", tags=["Stock Notifications"])
app.include_router(campaigns_router, prefix="/api", tags=["Campaigns"])
app.include_router(oauth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(design_templates_router, tags=["Design Templates"])
app.include_router(logos_router, tags=["Logos"])
app.include_router(customer_designs_router, tags=["Customer Designs"])
app.include_router(mockup_templates_router, tags=["Mockup Templates"])
app.include_router(product_bundles_router, tags=["Product Bundles"])
app.include_router(user_projects_router, tags=["User Projects"])
app.include_router(trending_templates_router, tags=["Trending Templates"])
app.include_router(recommendations_router, tags=["Recommendations"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
