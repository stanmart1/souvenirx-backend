"""
User Projects API Endpoints
Manages user's design projects (in-progress and completed)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.database import get_db
from app.models.user_project import UserProject
from app.models.user import User
from app.dependencies import get_current_user, require_admin
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/user-projects", tags=["User Projects"])


# Pydantic schemas
class UserProjectCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    product_id: str
    template_id: Optional[str] = None
    design_id: Optional[str] = None
    project_data: Optional[dict] = None
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    current_step: int = 1
    total_steps: int = 4


class UserProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    design_id: Optional[str] = None
    template_id: Optional[str] = None
    project_data: Optional[dict] = None
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    current_step: Optional[int] = None


class UserProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    status: str
    design_id: Optional[str]
    template_id: Optional[str]
    product_id: str
    project_data: Optional[dict]
    thumbnail_url: Optional[str]
    preview_url: Optional[str]
    completion_percentage: int
    current_step: int
    total_steps: int
    last_edited_at: Optional[str]
    completed_at: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    time_ago: Optional[str] = None

    class Config:
        from_attributes = True


# User endpoints
@router.get("/my-projects", response_model=List[UserProjectResponse])
async def get_my_projects(
    status: Optional[str] = Query(None, description="Filter by status: draft, in_progress, completed, archived"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's projects"""
    query = db.query(UserProject).filter(UserProject.user_id == current_user.id)
    
    if status:
        query = query.filter(UserProject.status == status)
    
    projects = query.order_by(desc(UserProject.last_edited_at)).offset(skip).limit(limit).all()
    
    # Add time_ago to response
    result = []
    for project in projects:
        project_dict = project.to_dict()
        project_dict['time_ago'] = project.get_time_ago()
        result.append(project_dict)
    
    return result


@router.get("/my-projects/recent", response_model=List[UserProjectResponse])
async def get_recent_projects(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's recent projects (for home screen)"""
    projects = db.query(UserProject).filter(
        and_(
            UserProject.user_id == current_user.id,
            or_(
                UserProject.status == 'in_progress',
                UserProject.status == 'completed'
            )
        )
    ).order_by(desc(UserProject.last_edited_at)).limit(limit).all()
    
    result = []
    for project in projects:
        project_dict = project.to_dict()
        project_dict['time_ago'] = project.get_time_ago()
        result.append(project_dict)
    
    return result


@router.get("/my-projects/{project_id}", response_model=UserProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific project"""
    project = db.query(UserProject).filter(
        and_(
            UserProject.id == uuid.UUID(project_id),
            UserProject.user_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_dict = project.to_dict()
    project_dict['time_ago'] = project.get_time_ago()
    
    return project_dict


@router.post("/", response_model=UserProjectResponse)
async def create_project(
    project_data: UserProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project"""
    # Calculate initial completion percentage
    completion = int((project_data.current_step / project_data.total_steps) * 100)
    
    project = UserProject(
        user_id=current_user.id,
        **project_data.dict(),
        status='in_progress',
        completion_percentage=completion
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    project_dict = project.to_dict()
    project_dict['time_ago'] = project.get_time_ago()
    
    return project_dict


@router.put("/{project_id}", response_model=UserProjectResponse)
async def update_project(
    project_id: str,
    project_data: UserProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a project"""
    project = db.query(UserProject).filter(
        and_(
            UserProject.id == uuid.UUID(project_id),
            UserProject.user_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update fields
    update_data = project_data.dict(exclude_unset=True)
    
    # Recalculate completion if step changed
    if 'current_step' in update_data:
        update_data['completion_percentage'] = int((update_data['current_step'] / project.total_steps) * 100)
    
    # Set completed_at if status changed to completed
    if update_data.get('status') == 'completed' and project.status != 'completed':
        update_data['completed_at'] = datetime.now(timezone.utc)
        update_data['completion_percentage'] = 100
    
    for key, value in update_data.items():
        setattr(project, key, value)
    
    # Update last_edited_at
    project.last_edited_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(project)
    
    project_dict = project.to_dict()
    project_dict['time_ago'] = project.get_time_ago()
    
    return project_dict


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a project"""
    project = db.query(UserProject).filter(
        and_(
            UserProject.id == uuid.UUID(project_id),
            UserProject.user_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/complete")
async def complete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a project as completed"""
    project = db.query(UserProject).filter(
        and_(
            UserProject.id == uuid.UUID(project_id),
            UserProject.user_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.status = 'completed'
    project.completion_percentage = 100
    project.completed_at = datetime.now(timezone.utc)
    project.last_edited_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"message": "Project marked as completed"}


@router.post("/{project_id}/archive")
async def archive_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive a project"""
    project = db.query(UserProject).filter(
        and_(
            UserProject.id == uuid.UUID(project_id),
            UserProject.user_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.status = 'archived'
    project.last_edited_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"message": "Project archived"}


@router.get("/stats/summary")
async def get_project_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's project statistics"""
    total = db.query(UserProject).filter(UserProject.user_id == current_user.id).count()
    
    in_progress = db.query(UserProject).filter(
        and_(
            UserProject.user_id == current_user.id,
            UserProject.status == 'in_progress'
        )
    ).count()
    
    completed = db.query(UserProject).filter(
        and_(
            UserProject.user_id == current_user.id,
            UserProject.status == 'completed'
        )
    ).count()
    
    return {
        'total': total,
        'in_progress': in_progress,
        'completed': completed,
        'draft': total - in_progress - completed
    }


# Admin endpoints
@router.get("/admin/all", response_model=List[UserProjectResponse], dependencies=[Depends(require_admin)])
async def get_all_projects_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects (Admin only)"""
    query = db.query(UserProject)
    
    if status:
        query = query.filter(UserProject.status == status)
    
    projects = query.order_by(desc(UserProject.created_at)).offset(skip).limit(limit).all()
    
    result = []
    for project in projects:
        project_dict = project.to_dict()
        project_dict['time_ago'] = project.get_time_ago()
        result.append(project_dict)
    
    return result


@router.get("/admin/stats", dependencies=[Depends(require_admin)])
async def get_all_project_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overall project statistics (Admin only)"""
    total = db.query(UserProject).count()
    in_progress = db.query(UserProject).filter(UserProject.status == 'in_progress').count()
    completed = db.query(UserProject).filter(UserProject.status == 'completed').count()
    
    # Get projects by product type
    from sqlalchemy import func
    by_product = db.query(
        UserProject.product_id,
        func.count(UserProject.id).label('count')
    ).group_by(UserProject.product_id).all()
    
    return {
        'total': total,
        'in_progress': in_progress,
        'completed': completed,
        'by_product': [{'product_id': str(p[0]), 'count': p[1]} for p in by_product]
    }
