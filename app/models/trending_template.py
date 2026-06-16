"""
Trending Template Model
Tracks and manages trending design templates for home screen
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class TrendingTemplate(Base):
    """Trending Template model - manages featured/trending templates"""
    
    __tablename__ = "trending_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Template reference
    template_id = Column(UUID(as_uuid=True), ForeignKey('design_templates.id'), nullable=False, index=True)
    
    # Display info
    display_name = Column(String(200))  # Override template name if needed
    display_order = Column(Integer, default=0, index=True)  # For sorting
    
    # Trending metrics
    trending_score = Column(DECIMAL(5, 2), default=0.0)  # Calculated score
    view_count_24h = Column(Integer, default=0)  # Views in last 24 hours
    usage_count_7d = Column(Integer, default=0)  # Uses in last 7 days
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_featured = Column(Boolean, default=False)  # Show in featured section
    
    # Availability
    featured_from = Column(DateTime(timezone=True))
    featured_until = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    template = relationship("DesignTemplate", foreign_keys=[template_id])
    
    def __repr__(self):
        return f"<TrendingTemplate {self.display_name or 'Template'}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        result = {
            'id': str(self.id),
            'template_id': str(self.template_id),
            'display_name': self.display_name,
            'display_order': self.display_order,
            'trending_score': float(self.trending_score) if self.trending_score else 0.0,
            'view_count_24h': self.view_count_24h,
            'usage_count_7d': self.usage_count_7d,
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'featured_from': self.featured_from.isoformat() if self.featured_from else None,
            'featured_until': self.featured_until.isoformat() if self.featured_until else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Include template data if available
        if self.template:
            result['template'] = {
                'id': str(self.template.id),
                'name': self.template.name,
                'slug': self.template.slug,
                'category': self.template.category,
                'style': self.template.style,
                'thumbnail': self.template.thumbnail,
                'preview_images': self.template.preview_images,
                'is_premium': self.template.is_premium,
                'premium_price': self.template.premium_price,
            }
        
        return result
