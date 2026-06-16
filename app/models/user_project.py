"""
User Project Model
Represents user's design projects (in-progress or completed)
"""

from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class UserProject(Base):
    """User Project model - tracks user's design projects"""
    
    __tablename__ = "user_projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    
    # Project info
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Status
    status = Column(String(50), default='in_progress', index=True)
    # Statuses: draft, in_progress, completed, archived
    
    # Design reference
    design_id = Column(UUID(as_uuid=True), ForeignKey('customer_designs.id'), nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey('design_templates.id'), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'), nullable=False)
    
    # Project data
    project_data = Column(JSONB)
    # Example: {
    #   "product_type": "tote_bag",
    #   "template_name": "Classic Script",
    #   "customizations": {
    #     "text": "Good times Great people",
    #     "color": "Navy Blue",
    #     "font": "Script"
    #   },
    #   "progress": {
    #     "step": 3,
    #     "total_steps": 4,
    #     "completed_steps": ["product", "template", "customize"]
    #   }
    # }
    
    # Media
    thumbnail_url = Column(String(500))
    preview_url = Column(String(500))
    
    # Progress tracking
    completion_percentage = Column(Integer, default=0)  # 0-100
    current_step = Column(Integer, default=1)  # Current step in creation flow
    total_steps = Column(Integer, default=4)  # Total steps
    
    # Timestamps
    last_edited_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="projects")
    design = relationship("CustomerDesign", foreign_keys=[design_id])
    template = relationship("DesignTemplate", foreign_keys=[template_id])
    product = relationship("Product", foreign_keys=[product_id])
    
    def __repr__(self):
        return f"<UserProject {self.name} - {self.status}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'design_id': str(self.design_id) if self.design_id else None,
            'template_id': str(self.template_id) if self.template_id else None,
            'product_id': str(self.product_id),
            'project_data': self.project_data,
            'thumbnail_url': self.thumbnail_url,
            'preview_url': self.preview_url,
            'completion_percentage': self.completion_percentage,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'last_edited_at': self.last_edited_at.isoformat() if self.last_edited_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_time_ago(self):
        """Get human-readable time since last edit"""
        if not self.last_edited_at:
            return "Never"
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        delta = now - self.last_edited_at
        
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
