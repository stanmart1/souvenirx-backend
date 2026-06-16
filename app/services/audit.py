"""Audit logging service for tracking admin actions"""
import json
from typing import Any, Dict, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    admin_id: str | uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: str,
    changes: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """
    Log an administrative action to the audit trail.
    
    Args:
        db: Database session
        admin_id: UUID of the admin performing the action
        action: Action being performed (e.g., "update_customer", "reset_password")
        resource_type: Type of resource being acted upon (e.g., "user", "order")
        resource_id: ID of the specific resource
        changes: Optional dict of changes made (will be JSON serialized)
        ip_address: Optional IP address of the admin
        user_agent: Optional user agent string
        
    Returns:
        The created AuditLog instance
        
    Example:
        await log_audit(
            db=db,
            admin_id=str(admin.id),
            action="update_customer",
            resource_type="user",
            resource_id=customer_id,
            changes={"email": {"old": "old@example.com", "new": "new@example.com"}},
            ip_address="192.168.1.1"
        )
    """
    # Convert admin_id to UUID if it's a string
    if isinstance(admin_id, str):
        admin_id = uuid.UUID(admin_id)
    
    # Serialize changes to JSON if provided
    changes_json = None
    if changes:
        try:
            changes_json = json.dumps(changes, default=str)
        except (TypeError, ValueError) as e:
            print(f"Failed to serialize audit log changes: {e}")
            changes_json = json.dumps({"error": "Failed to serialize changes"})
    
    # Create audit log entry
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes_json,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    db.add(log)
    await db.flush()
    
    return log


def get_client_ip(request) -> Optional[str]:
    """Extract client IP address from request"""
    if not request or not request.client:
        return None
    return request.client.host


def get_user_agent(request) -> Optional[str]:
    """Extract user agent from request headers"""
    if not request or not request.headers:
        return None
    return request.headers.get("user-agent")
