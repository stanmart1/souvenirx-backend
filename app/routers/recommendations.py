"""
Personalized Recommendations API
Provides personalized content for home screen based on user behavior
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from app.database import get_db
from app.models.user import User
from app.models.product_bundle import ProductBundle
from app.models.trending_template import TrendingTemplate
from app.models.user_project import UserProject
from app.models.order import Order
from app.models.product import Product
from app.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


# Response schemas
class HomeScreenData(BaseModel):
    greeting: str
    featured_bundles: List[dict]
    trending_templates: List[dict]
    recent_projects: List[dict]
    recommended_products: List[dict]
    personalized_message: Optional[str] = None

    class Config:
        from_attributes = True


def get_time_based_greeting(user_name: str) -> str:
    """Generate time-based personalized greeting"""
    now = datetime.now()
    hour = now.hour

    if 5 <= hour < 12:
        greeting = f"Good morning, {user_name} 👋"
    elif 12 <= hour < 17:
        greeting = f"Good afternoon, {user_name} 👋"
    elif 17 <= hour < 22:
        greeting = f"Good evening, {user_name} 👋"
    else:
        greeting = f"Hello, {user_name} 👋"

    return greeting


async def get_personalized_message(user: User, db: AsyncSession) -> Optional[str]:
    """Generate personalized message based on user activity"""
    # Check if user has any projects
    project_count = (
        await db.execute(
            select(func.count())
            .select_from(UserProject)
            .where(UserProject.user_id == user.id)
        )
    ).scalar()

    if project_count == 0:
        return "Start your first custom design today ✨"

    # Check for in-progress projects
    in_progress = (
        await db.execute(
            select(func.count())
            .select_from(UserProject)
            .where(
                and_(
                    UserProject.user_id == user.id,
                    UserProject.status == "in_progress",
                )
            )
        )
    ).scalar()

    if in_progress > 0:
        return f"You have {in_progress} project{'s' if in_progress > 1 else ''} waiting for you 🎨"

    # Check recent orders
    recent_order = (
        await db.execute(
            select(Order)
            .where(Order.user_id == user.id)
            .order_by(desc(Order.created_at))
        )
    ).scalar_one_or_none()

    if recent_order:
        days_since = (datetime.now(timezone.utc) - recent_order.created_at).days
        if days_since < 7:
            return "Create something new for your next event 🎉"

    return "Create something memorable today"


@router.get("/home-screen", response_model=HomeScreenData)
async def get_home_screen_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get personalized home screen data"""
    now = datetime.now(timezone.utc)

    # 1. Generate greeting
    greeting = get_time_based_greeting(current_user.full_name.split()[0])

    # 2. Get featured bundles
    featured_bundles = (
        await db.execute(
            select(ProductBundle)
            .where(
                and_(
                    ProductBundle.is_featured == True,
                    ProductBundle.is_active == True,
                    ProductBundle.stock_status == "in_stock",
                    (ProductBundle.available_from == None)
                    | (ProductBundle.available_from <= now),
                    (ProductBundle.available_until == None)
                    | (ProductBundle.available_until >= now),
                )
            )
            .order_by(
                desc(ProductBundle.display_order),
                desc(ProductBundle.popularity_score),
            )
            .limit(5)
        )
    ).scalars().all()

    # 3. Get trending templates
    trending_templates = (
        await db.execute(
            select(TrendingTemplate)
            .options(selectinload(TrendingTemplate.template))
            .where(TrendingTemplate.is_active == True)
            .order_by(desc(TrendingTemplate.trending_score))
            .limit(8)
        )
    ).scalars().all()

    # 4. Get user's recent projects
    recent_projects = (
        await db.execute(
            select(UserProject)
            .where(UserProject.user_id == current_user.id)
            .order_by(desc(UserProject.last_edited_at))
            .limit(4)
        )
    ).scalars().all()

    # 5. Get recommended products based on user history
    recommended_products = await get_recommended_products(current_user, db)

    # 6. Generate personalized message
    personalized_message = await get_personalized_message(current_user, db)

    # Format response
    return {
        "greeting": greeting,
        "featured_bundles": [bundle.to_dict() for bundle in featured_bundles],
        "trending_templates": [template.to_dict() for template in trending_templates],
        "recent_projects": [
            {**project.to_dict(), "time_ago": project.get_time_ago()}
            for project in recent_projects
        ],
        "recommended_products": recommended_products,
        "personalized_message": personalized_message,
    }


async def get_recommended_products(user: User, db: AsyncSession) -> List[dict]:
    """Get personalized product recommendations"""
    # Get user's order history
    user_orders = (
        await db.execute(select(Order).where(Order.user_id == user.id))
    ).scalars().all()

    if not user_orders:
        # New user - return popular products
        products = (
            await db.execute(
                select(Product)
                .options(selectinload(Product.images))
                .where(Product.is_active == True)
                .order_by(desc(Product.created_at))
                .limit(6)
            )
        ).scalars().all()

        return [
            {
                "id": str(product.id),
                "name": product.name,
                "slug": product.slug,
                "price": product.base_price,
                "image_url": product.images[0].url if product.images else None,
                "category": product.category_id,
            }
            for product in products
        ]

    # Get categories user has ordered from
    from app.models.order import OrderItem

    ordered_product_ids = []
    for order in user_orders:
        items = (
            await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
        ).scalars().all()
        ordered_product_ids.extend([item.product_id for item in items])

    if not ordered_product_ids:
        # Fallback to popular products
        products = (
            await db.execute(
                select(Product)
                .options(selectinload(Product.images))
                .where(Product.is_active == True)
                .limit(6)
            )
        ).scalars().all()
    else:
        # Get products from same categories
        ordered_products = (
            await db.execute(
                select(Product).where(Product.id.in_(ordered_product_ids))
            )
        ).scalars().all()

        categories = list(
            set([p.category_id for p in ordered_products if p.category_id])
        )

        if categories:
            # Recommend products from same categories
            products = (
                await db.execute(
                    select(Product)
                    .options(selectinload(Product.images))
                    .where(
                        and_(
                            Product.is_active == True,
                            Product.category_id.in_(categories),
                            ~Product.id.in_(ordered_product_ids),  # Exclude already ordered
                        )
                    )
                    .limit(6)
                )
            ).scalars().all()
        else:
            products = (
                await db.execute(
                    select(Product)
                    .options(selectinload(Product.images))
                    .where(Product.is_active == True)
                    .limit(6)
                )
            ).scalars().all()

    return [
        {
            "id": str(product.id),
            "name": product.name,
            "slug": product.slug,
            "price": product.base_price,
            "image_url": product.images[0].url if product.images else None,
            "category": product.category_id,
        }
        for product in products
    ]


@router.get("/for-you")
async def get_personalized_recommendations(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get personalized recommendations (templates, products, bundles)"""
    # Get user's recent activity
    recent_projects = (
        await db.execute(
            select(UserProject)
            .where(UserProject.user_id == current_user.id)
            .order_by(desc(UserProject.created_at))
            .limit(5)
        )
    ).scalars().all()

    # Extract template IDs from projects
    template_ids = [p.template_id for p in recent_projects if p.template_id]

    recommendations = {
        "templates": [],
        "products": [],
        "bundles": [],
    }

    if template_ids:
        # Get similar templates (same category/style)
        from app.models.design_template import DesignTemplate

        used_templates = (
            await db.execute(
                select(DesignTemplate).where(DesignTemplate.id.in_(template_ids))
            )
        ).scalars().all()

        categories = list(
            set([t.category for t in used_templates if t.category])
        )

        if categories:
            similar_templates = (
                await db.execute(
                    select(DesignTemplate)
                    .where(
                        and_(
                            DesignTemplate.is_active == True,
                            DesignTemplate.category.in_(categories),
                            ~DesignTemplate.id.in_(template_ids),
                        )
                    )
                    .limit(5)
                )
            ).scalars().all()

            recommendations["templates"] = [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "category": t.category,
                    "thumbnail": t.thumbnail_url,
                    "is_premium": t.is_premium,
                }
                for t in similar_templates
            ]

    # Get recommended products
    recommendations["products"] = await get_recommended_products(current_user, db)

    # Get relevant bundles
    bundles = (
        await db.execute(
            select(ProductBundle)
            .where(
                and_(
                    ProductBundle.is_active == True,
                    ProductBundle.stock_status == "in_stock",
                )
            )
            .order_by(desc(ProductBundle.popularity_score))
            .limit(3)
        )
    ).scalars().all()

    recommendations["bundles"] = [bundle.to_dict() for bundle in bundles]

    return recommendations


@router.get("/continue-designing")
async def get_continue_designing(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get projects user can continue working on"""
    projects = (
        await db.execute(
            select(UserProject)
            .where(
                and_(
                    UserProject.user_id == current_user.id,
                    UserProject.status == "in_progress",
                    UserProject.completion_percentage < 100,
                )
            )
            .order_by(desc(UserProject.last_edited_at))
            .limit(5)
        )
    ).scalars().all()

    return {
        "projects": [
            {**project.to_dict(), "time_ago": project.get_time_ago()}
            for project in projects
        ]
    }
