"""
Product Bundles API Endpoints
Manages product bundles/packs for home screen
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.database import get_db
from app.models.product_bundle import ProductBundle
from app.models.user import User
from app.dependencies import get_current_user, require_admin
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/product-bundles", tags=["Product Bundles"])


# Pydantic schemas
class ProductBundleCreate(BaseModel):
    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=200)
    description: Optional[str] = None
    tagline: Optional[str] = Field(None, max_length=500)
    original_price: int = Field(..., gt=0)
    discounted_price: int = Field(..., gt=0)
    product_ids: List[str] = Field(..., min_items=1)
    bundle_data: Optional[dict] = None
    image_url: str = Field(..., max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    banner_images: Optional[List[str]] = None
    is_featured: bool = False
    is_active: bool = True
    display_order: int = 0
    delivery_time: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    stock_status: str = 'in_stock'
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ProductBundleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    slug: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    tagline: Optional[str] = Field(None, max_length=500)
    original_price: Optional[int] = Field(None, gt=0)
    discounted_price: Optional[int] = Field(None, gt=0)
    product_ids: Optional[List[str]] = None
    bundle_data: Optional[dict] = None
    image_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    banner_images: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
    delivery_time: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    stock_status: Optional[str] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ProductBundleResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    tagline: Optional[str]
    original_price: int
    discounted_price: int
    discount_percentage: Optional[int]
    product_ids: List[str]
    bundle_data: Optional[dict]
    image_url: str
    thumbnail_url: Optional[str]
    banner_images: Optional[List[str]]
    is_featured: bool
    is_active: bool
    display_order: int
    delivery_time: Optional[str]
    category: Optional[str]
    tags: Optional[List[str]]
    stock_status: str
    available_from: Optional[str]
    available_until: Optional[str]
    view_count: int
    purchase_count: int
    popularity_score: float
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# Helper functions
def calculate_discount_percentage(original: int, discounted: int) -> int:
    """Calculate discount percentage"""
    if original <= 0:
        return 0
    return int(((original - discounted) / original) * 100)


# Public endpoints
@router.get("/featured", response_model=List[ProductBundleResponse])
async def get_featured_bundles(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get featured product bundles for home screen"""
    now = datetime.now(timezone.utc)
    
    bundles = db.query(ProductBundle).filter(
        and_(
            ProductBundle.is_featured == True,
            ProductBundle.is_active == True,
            ProductBundle.stock_status == 'in_stock',
            # Check availability dates
            (ProductBundle.available_from == None) | (ProductBundle.available_from <= now),
            (ProductBundle.available_until == None) | (ProductBundle.available_until >= now)
        )
    ).order_by(
        desc(ProductBundle.display_order),
        desc(ProductBundle.popularity_score)
    ).limit(limit).all()
    
    return [bundle.to_dict() for bundle in bundles]


@router.get("/", response_model=List[ProductBundleResponse])
async def get_all_bundles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    is_active: bool = True,
    db: Session = Depends(get_db)
):
    """Get all product bundles with filters"""
    query = db.query(ProductBundle)
    
    if is_active:
        query = query.filter(ProductBundle.is_active == True)
    
    if category:
        query = query.filter(ProductBundle.category == category)
    
    bundles = query.order_by(
        desc(ProductBundle.display_order),
        desc(ProductBundle.created_at)
    ).offset(skip).limit(limit).all()
    
    return [bundle.to_dict() for bundle in bundles]


@router.get("/{bundle_id}", response_model=ProductBundleResponse)
async def get_bundle(
    bundle_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific product bundle"""
    bundle = db.query(ProductBundle).filter(ProductBundle.id == uuid.UUID(bundle_id)).first()
    
    if not bundle:
        raise HTTPException(status_code=404, detail="Product bundle not found")
    
    # Increment view count
    bundle.view_count += 1
    db.commit()
    
    return bundle.to_dict()


@router.get("/slug/{slug}", response_model=ProductBundleResponse)
async def get_bundle_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get a product bundle by slug"""
    bundle = db.query(ProductBundle).filter(ProductBundle.slug == slug).first()
    
    if not bundle:
        raise HTTPException(status_code=404, detail="Product bundle not found")
    
    # Increment view count
    bundle.view_count += 1
    db.commit()
    
    return bundle.to_dict()


# Admin endpoints
@router.post("/", response_model=ProductBundleResponse, dependencies=[Depends(require_admin)])
async def create_bundle(
    bundle_data: ProductBundleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new product bundle (Admin only)"""
    # Check if slug already exists
    existing = db.query(ProductBundle).filter(ProductBundle.slug == bundle_data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bundle with this slug already exists")
    
    # Calculate discount percentage
    discount_pct = calculate_discount_percentage(
        bundle_data.original_price,
        bundle_data.discounted_price
    )
    
    # Create bundle
    bundle = ProductBundle(
        **bundle_data.dict(),
        discount_percentage=discount_pct,
        view_count=0,
        purchase_count=0,
        popularity_score=0.0
    )
    
    db.add(bundle)
    db.commit()
    db.refresh(bundle)
    
    return bundle.to_dict()


@router.put("/{bundle_id}", response_model=ProductBundleResponse, dependencies=[Depends(require_admin)])
async def update_bundle(
    bundle_id: str,
    bundle_data: ProductBundleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a product bundle (Admin only)"""
    bundle = db.query(ProductBundle).filter(ProductBundle.id == uuid.UUID(bundle_id)).first()
    
    if not bundle:
        raise HTTPException(status_code=404, detail="Product bundle not found")
    
    # Update fields
    update_data = bundle_data.dict(exclude_unset=True)
    
    # Recalculate discount if prices changed
    if 'original_price' in update_data or 'discounted_price' in update_data:
        original = update_data.get('original_price', bundle.original_price)
        discounted = update_data.get('discounted_price', bundle.discounted_price)
        update_data['discount_percentage'] = calculate_discount_percentage(original, discounted)
    
    for key, value in update_data.items():
        setattr(bundle, key, value)
    
    db.commit()
    db.refresh(bundle)
    
    return bundle.to_dict()


@router.delete("/{bundle_id}", dependencies=[Depends(require_admin)])
async def delete_bundle(
    bundle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a product bundle (Admin only)"""
    bundle = db.query(ProductBundle).filter(ProductBundle.id == uuid.UUID(bundle_id)).first()
    
    if not bundle:
        raise HTTPException(status_code=404, detail="Product bundle not found")
    
    db.delete(bundle)
    db.commit()
    
    return {"message": "Product bundle deleted successfully"}


@router.post("/{bundle_id}/increment-purchase", dependencies=[Depends(get_current_user)])
async def increment_purchase_count(
    bundle_id: str,
    db: Session = Depends(get_db)
):
    """Increment purchase count for a bundle"""
    bundle = db.query(ProductBundle).filter(ProductBundle.id == uuid.UUID(bundle_id)).first()
    
    if not bundle:
        raise HTTPException(status_code=404, detail="Product bundle not found")
    
    bundle.purchase_count += 1
    
    # Update popularity score (simple algorithm: purchases * 2 + views)
    bundle.popularity_score = (bundle.purchase_count * 2) + (bundle.view_count * 0.1)
    
    db.commit()
    
    return {"message": "Purchase count incremented"}


@router.get("/categories/list")
async def get_bundle_categories(db: Session = Depends(get_db)):
    """Get list of all bundle categories"""
    categories = db.query(ProductBundle.category).filter(
        ProductBundle.category != None,
        ProductBundle.is_active == True
    ).distinct().all()
    
    return {"categories": [cat[0] for cat in categories if cat[0]]}
