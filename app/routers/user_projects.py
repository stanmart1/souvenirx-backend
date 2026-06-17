"""
User Projects API Endpoints
Manages user's design projects (in-progress and completed)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's projects"""
    query = select(UserProject).where(UserProject.user_id == current_user.id)

    if status:
        query = query.where(UserProject.status == status)

    projects = (
        await db.execute(
            query.order_by(desc(UserProject.last_edited_at)).offset(skip).limit(limit)
        )
    ).scalars().all()

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's recent projects (for home screen)"""
    projects = (
        await db.execute(
            select(UserProject).where(
                and_(
                    UserProject.user_id == current_user.id,
                    or_(
                        UserProject.status == 'in_progress',
                        UserProject.status == 'completed'
                    )
                )
            ).order_by(desc(UserProject.last_edited_at)).limit(limit)
        )
    ).scalars().all()

    result = []
    for project in projects:
        project_dict = project.to_dict()
        project_dict['time_ago'] = project.get_time_ago()
        result.append(project_dict)

    return result


@router.get("/my-projects/{project_id}", response_model=UserProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific project"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project_id format")

    project = (
        await db.execute(
            select(UserProject).where(
                and_(
                    UserProject.id == project_uuid,
                    UserProject.user_id == current_user.id
                )
            )
        )
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_dict = project.to_dict()
    project_dict['time_ago'] = project.get_time_ago()

    return project_dict


@router.post("/", response_model=UserProjectResponse)
async def create_project(
    project_data: UserProjectCreate,
    db: AsyncSession = Depends(get_db),
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
    await db.commit()
    await db.refresh(project)

    project_dict = project.to_dict()
    project_dict['time_ago'] = project.get_time_ago()

    return project_dict


@router.put("/{project_id}", response_model=UserProjectResponse)
async def update_project(
    project_id: str,
    project_data: UserProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a project"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project_id format")

    project = (
        await db.execute(
            select(UserProject).where(
                and_(
                    UserProject.id == project_uuid,
                    UserProject.user_id == current_user.id
                )
            )
        )
    ).scalar_one_or_none()

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

    await db.commit()
    await db.refresh(project)

    project_dict = project.to_dict()
    project_dict['time_ago'] = project.get_time_ago()

    return project_dict


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a project"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project_id format")

    project = (
        await db.execute(
            select(UserProject).where(
                and_(
                    UserProject.id == project_uuid,
                    UserProject.user_id == current_user.id
                )
            )
        )
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()

    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/complete")
async def complete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a project as completed"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project_id format")

    project = (
        await db.execute(
            select(UserProject).where(
                and_(
                    UserProject.id == project_uuid,
                    UserProject.user_id == current_user.id
                )
            )
        )
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = 'completed'
    project.completion_percentage = 100
    project.completed_at = datetime.now(timezone.utc)
    project.last_edited_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Project marked as completed"}


@router.post("/{project_id}/archive")
async def archive_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive a project"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project_id format")

    project = (
        await db.execute(
            select(UserProject).where(
                and_(
                    UserProject.id == project_uuid,
                    UserProject.user_id == current_user.id
                )
            )
        )
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = 'archived'
    project.last_edited_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Project archived"}


@router.get("/stats/summary")
async def get_project_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's project statistics"""
    total = (
        await db.execute(
            select(func.count()).select_from(UserProject).where(
                UserProject.user_id == current_user.id
            )
        )
    ).scalar()

    in_progress = (
        await db.execute(
            select(func.count()).select_from(UserProject).where(
                and_(
                    UserProject.user_id == current_user.id,
                    UserProject.status == 'in_progress'
                )
            )
        )
    ).scalar()

    completed = (
        await db.execute(
            select(func.count()).select_from(UserProject).where(
                and_(
                    UserProject.user_id == current_user.id,
                    UserProject.status == 'completed'
                )
            )
        )
    ).scalar()

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects (Admin only)"""
    query = select(UserProject)

    if status:
        query = query.where(UserProject.status == status)

    projects = (
        await db.execute(
            query.order_by(desc(UserProject.created_at)).offset(skip).limit(limit)
        )
    ).scalars().all()

    result = []
    for project in projects:
        project_dict = project.to_dict()
        project_dict['time_ago'] = project.get_time_ago()
        result.append(project_dict)

    return result


@router.get("/admin/stats", dependencies=[Depends(require_admin)])
async def get_all_project_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overall project statistics (Admin only)"""
    total = (
        await db.execute(select(func.count()).select_from(UserProject))
    ).scalar()

    in_progress = (
        await db.execute(
            select(func.count()).select_from(UserProject).where(
                UserProject.status == 'in_progress'
            )
        )
    ).scalar()

    completed = (
        await db.execute(
            select(func.count()).select_from(UserProject).where(
                UserProject.status == 'completed'
            )
        )
    ).scalar()

    # Get projects by product type
    by_product = (
        await db.execute(
            select(UserProject.product_id, func.count(UserProject.id).label('count'))
            .group_by(UserProject.product_id)
        )
    ).all()

    return {
        'total': total,
        'in_progress': in_progress,
        'completed': completed,
        'by_product': [{'product_id': str(p[0]), 'count': p[1]} for p in by_product]
    }


@router.delete("/admin/{project_id}", dependencies=[Depends(require_admin)])
async def admin_delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete any project by ID (Admin only)"""
    project = (
        await db.execute(select(UserProject).where(UserProject.id == project_id))
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted successfully"}
