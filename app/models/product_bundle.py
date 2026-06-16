"""
Product Bundle Model
Represents product packs/bundles like "Summer Reunion Pack"
"""

from sqlalchemy import Column, String, Integer, Boolean, ARRAY, Text, DECIMAL, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.database import Base


class ProductBundle(Base):
    """Product Bundle/Pack model"""
    
    __tablename__ = "product_bundles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic info
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text)
    tagline = Column(String(500))  # e.g., "Start from a tote, mug & thank-you card set"
    
    # Pricing
    original_price = Column(Integer, nullable=False)  # in cents
    discounted_price = Column(Integer, nullable=False)  # in cents
    discount_percentage = Column(Integer)  # calculated discount %
    
    # Products in bundle (array of product IDs)
    product_ids = Column(ARRAY(String), nullable=False)
    
    # Bundle details
    bundle_data = Column(JSONB)  # Flexible data: quantities, variants, etc.
    # Example: {
    #   "products": [
    #     {"product_id": "xxx", "quantity": 1, "variant": "Navy Blue"},
    #     {"product_id": "yyy", "quantity": 1, "variant": "White"}
    #   ],
    #   "savings": 1490
    # }
    
    # Media
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    banner_images = Column(ARRAY(String))  # Multiple images for carousel
    
    # Display settings
    is_featured = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    display_order = Column(Integer, default=0)  # For sorting featured bundles
    
    # Delivery info
    delivery_time = Column(String(100))  # e.g., "2-3 day delivery"
    
    # Category/Tags
    category = Column(String(100))  # e.g., "Events", "Corporate", "Personal"
    tags = Column(ARRAY(String))  # e.g., ["reunion", "summer", "gifts"]
    
    # Availability
    stock_status = Column(String(50), default='in_stock')  # in_stock, low_stock, out_of_stock
    available_from = Column(DateTime(timezone=True))
    available_until = Column(DateTime(timezone=True))
    
    # Analytics
    view_count = Column(Integer, default=0)
    purchase_count = Column(Integer, default=0)
    popularity_score = Column(DECIMAL(5, 2), default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<ProductBundle {self.name}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'tagline': self.tagline,
            'original_price': self.original_price,
            'discounted_price': self.discounted_price,
            'discount_percentage': self.discount_percentage,
            'product_ids': self.product_ids,
            'bundle_data': self.bundle_data,
            'image_url': self.image_url,
            'thumbnail_url': self.thumbnail_url,
            'banner_images': self.banner_images,
            'is_featured': self.is_featured,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'delivery_time': self.delivery_time,
            'category': self.category,
            'tags': self.tags,
            'stock_status': self.stock_status,
            'available_from': self.available_from.isoformat() if self.available_from else None,
            'available_until': self.available_until.isoformat() if self.available_until else None,
            'view_count': self.view_count,
            'purchase_count': self.purchase_count,
            'popularity_score': float(self.popularity_score) if self.popularity_score else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
