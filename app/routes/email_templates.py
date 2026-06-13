"""Email and SMS templates management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.user import User
from app.models.settings import EmailTemplate, SmsTemplate
from app.schemas.email_template import EmailTemplateCreate, EmailTemplateUpdate
from app.data.email_templates import DEFAULT_EMAIL_TEMPLATES
from app.data.sms_templates import DEFAULT_SMS_TEMPLATES

router = APIRouter()


@router.get("/email-templates")
async def list_email_templates(
    is_active: bool | None = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all email templates."""
    query = select(EmailTemplate)
    if is_active is not None:
        query = query.where(EmailTemplate.is_active == is_active)
    
    query = query.order_by(EmailTemplate.name)
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return [
        {
            "id": template.id,
            "name": template.name,
            "subject": template.subject,
            "htmlContent": template.html_content,
            "variables": template.variables,
            "isActive": template.is_active,
            "createdAt": template.created_at.isoformat(),
            "updatedAt": template.updated_at.isoformat(),
        }
        for template in templates
    ]


@router.get("/email-templates/{template_name}")
async def get_email_template(
    template_name: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific email template by name."""
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.name == template_name))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "subject": template.subject,
        "htmlContent": template.html_content,
        "variables": template.variables,
        "isActive": template.is_active,
        "createdAt": template.created_at.isoformat(),
        "updatedAt": template.updated_at.isoformat(),
    }


@router.post("/email-templates")
async def create_email_template(
    body: EmailTemplateCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new email template."""
    template = EmailTemplate(
        name=body.name,
        subject=body.subject,
        html_content=body.html_content,
        variables=body.variables,
        is_active=body.is_active,
    )
    db.add(template)
    await db.flush()
    
    return {"id": template.id, "message": "Email template created successfully"}


@router.put("/email-templates/{template_name}")
async def update_email_template(
    template_name: str,
    body: EmailTemplateUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing email template."""
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.name == template_name))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    if body.subject is not None:
        template.subject = body.subject
    if body.html_content is not None:
        template.html_content = body.html_content
    if body.variables is not None:
        template.variables = body.variables
    if body.is_active is not None:
        template.is_active = body.is_active
    
    await db.flush()
    return {"message": "Email template updated successfully"}


@router.post("/email-templates/{template_name}/preview")
async def preview_email_template(
    template_name: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Preview an email template with sample data."""
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.name == template_name))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    # Replace variables in the template
    html_content = template.html_content
    for key, value in body.get("variables", {}).items():
        html_content = html_content.replace(f"{{{{{key}}}}}", str(value))
    
    return {
        "subject": template.subject,
        "html": html_content,
    }


@router.post("/email-templates/seed")
async def seed_email_templates(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Seed default email templates with design system styling (no emojis)."""
    created_count = 0
    for template_data in DEFAULT_EMAIL_TEMPLATES:
        # Check if template already exists
        existing = await db.execute(select(EmailTemplate).where(EmailTemplate.name == template_data["name"]))
        if not existing.scalar_one_or_none():
            template = EmailTemplate(
                name=template_data["name"],
                subject=template_data["subject"],
                html_content=template_data["html_content"],
                variables=template_data["variables"],
                is_active=template_data["is_active"],
            )
            db.add(template)
            created_count += 1
    
    await db.flush()
    return {"message": f"Seeded {created_count} email templates"}


# --- SMS Templates Management ---
@router.get("/sms-templates")
async def list_sms_templates(
    is_active: bool | None = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all SMS templates."""
    query = select(SmsTemplate)
    if is_active is not None:
        query = query.where(SmsTemplate.is_active == is_active)
    
    query = query.order_by(SmsTemplate.name)
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return [
        {
            "id": template.id,
            "name": template.name,
            "template": template.template,
            "variables": template.variables,
            "isActive": template.is_active,
            "createdAt": template.created_at.isoformat(),
            "updatedAt": template.updated_at.isoformat(),
        }
        for template in templates
    ]


@router.get("/sms-templates/{template_name}")
async def get_sms_template(
    template_name: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific SMS template by name."""
    result = await db.execute(select(SmsTemplate).where(SmsTemplate.name == template_name))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="SMS template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "template": template.template,
        "variables": template.variables,
        "isActive": template.is_active,
        "createdAt": template.created_at.isoformat(),
        "updatedAt": template.updated_at.isoformat(),
    }


@router.post("/sms-templates")
async def create_sms_template(
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new SMS template."""
    template = SmsTemplate(
        name=body["name"],
        template=body["template"],
        variables=body.get("variables", {}),
        is_active=body.get("is_active", True),
    )
    db.add(template)
    await db.flush()
    
    return {"id": template.id, "message": "SMS template created successfully"}


@router.put("/sms-templates/{template_name}")
async def update_sms_template(
    template_name: str,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing SMS template."""
    result = await db.execute(select(SmsTemplate).where(SmsTemplate.name == template_name))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="SMS template not found")
    
    if "template" in body:
        template.template = body["template"]
    if "variables" in body:
        template.variables = body["variables"]
    if "is_active" in body:
        template.is_active = body["is_active"]
    
    await db.flush()
    return {"message": "SMS template updated successfully"}


@router.post("/sms-templates/seed")
async def seed_sms_templates(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Seed default SMS templates."""
    created_count = 0
    for template_name, template_text in DEFAULT_SMS_TEMPLATES.items():
        # Check if template already exists
        existing = await db.execute(select(SmsTemplate).where(SmsTemplate.name == template_name))
        if not existing.scalar_one_or_none():
            # Extract variables from template
            import re
            variables = {}
            for match in re.findall(r'\{(\w+)\}', template_text):
                variables[match] = "string"
            
            template = SmsTemplate(
                name=template_name,
                template=template_text,
                variables=variables,
                is_active=True,
            )
            db.add(template)
            created_count += 1
    
    await db.flush()
    return {"message": f"Seeded {created_count} SMS templates"}
