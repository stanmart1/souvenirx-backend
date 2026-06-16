# Implementation Plan: Email Verification & User Management Upgrade

**Project:** SouvenirX Platform Security & Admin Features Enhancement  
**Date Created:** 2026-06-16  
**Total Tasks:** 51  
**Estimated Duration:** 3-4 weeks (1 developer)

---

## Overview

This document outlines the complete implementation plan to address all critical security issues and missing features identified in the Email Verification and User Management audit.

---

## Phase 1: Critical Security Fixes (Week 1)

**Priority:** 🔴 CRITICAL - Must be completed first  
**Estimated Time:** 5-7 days  
**Dependencies:** None

### 1.1 Email Verification Security (Days 1-2)

#### Backend Tasks

**Task 1.1.1:** Add verification token expiration to User model
- **File:** `souvenirx-backend/app/models/user.py`
- **Changes:**
  ```python
  verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
  ```
- **Status:** ⬜ Pending

**Task 1.1.2:** Create database migration
- **File:** `souvenirx-backend/alembic/versions/XXXX_add_verification_expiry.py`
- **Command:** `alembic revision --autogenerate -m "Add verification token expiration"`
- **Status:** ⬜ Pending

**Task 1.1.3:** Update registration endpoints
- **Files:** 
  - `souvenirx-backend/app/routes/auth.py` (lines 29-66, 69-116)
- **Changes:**
  ```python
  from datetime import timedelta
  user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
  ```
- **Endpoints affected:** `/api/auth/register`, `/api/auth/affiliate/register`
- **Status:** ⬜ Pending

**Task 1.1.4:** Add token expiration check in verify_email
- **File:** `souvenirx-backend/app/routes/auth.py` (lines 119-139)
- **Changes:**
  ```python
  if user.verification_token_expires_at and user.verification_token_expires_at < datetime.now(timezone.utc):
      raise HTTPException(status_code=400, detail="Verification link has expired. Please request a new one.")
  ```
- **Status:** ⬜ Pending

**Task 1.1.5:** Add rate limiting to verify-email endpoint
- **File:** `souvenirx-backend/app/routes/auth.py`
- **Changes:**
  ```python
  @router.post("/verify-email")
  async def verify_email(token: str, request: Request, db: AsyncSession = Depends(get_db)):
      client_ip = request.client.host if request.client else "unknown"
      if not await check_rate_limit(f"rl:verify:{client_ip}", 5, 300):
          raise HTTPException(status_code=429, detail="Too many verification attempts")
  ```
- **Status:** ⬜ Pending

**Task 1.1.6:** Invalidate old tokens on resend
- **File:** `souvenirx-backend/app/routes/auth.py` (lines 142-162)
- **Changes:** Already handled by updating `verification_token` field
- **Status:** ⬜ Pending

**Task 1.1.7:** Improve error messages
- **File:** `souvenirx-backend/app/routes/auth.py`
- **Changes:**
  ```python
  if not user:
      raise HTTPException(status_code=400, detail="Invalid verification link")
  if user.email_verified:
      raise HTTPException(status_code=400, detail="Email already verified")
  if user.verification_token_expires_at < datetime.now(timezone.utc):
      raise HTTPException(status_code=400, detail="Verification link expired. Request a new one.")
  ```
- **Status:** ⬜ Pending

**Task 1.1.8:** Update email template
- **File:** `souvenirx-backend/app/data/email_templates.py`
- **Changes:** Update line 60 to mention "This link expires in 24 hours"
- **Status:** ⬜ Pending

#### Testing

**Task 1.1.9:** Test verification flow
- Test valid token verification
- Test expired token (set expiry to past)
- Test already verified email
- Test invalid token
- Test rate limiting (6+ attempts)
- **Status:** ⬜ Pending

---

### 1.2 Audit Logging System (Days 3-4)

#### Backend Tasks

**Task 1.2.1:** Create AuditLog model
- **File:** `souvenirx-backend/app/models/audit_log.py` (NEW)
- **Content:**
  ```python
  import uuid
  from datetime import datetime
  from typing import Optional
  from sqlalchemy import String, ForeignKey, DateTime, func, Text
  from sqlalchemy.orm import Mapped, mapped_column, relationship
  from sqlalchemy.dialects.postgresql import UUID
  from app.database import Base
  
  class AuditLog(Base):
      __tablename__ = "audit_logs"
      
      id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
      admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
      action: Mapped[str] = mapped_column(String(100), nullable=False)
      resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
      resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
      changes: Mapped[Optional[str]] = mapped_column(Text)  # JSON string
      ip_address: Mapped[Optional[str]] = mapped_column(String(45))
      user_agent: Mapped[Optional[str]] = mapped_column(String(500))
      created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
      
      admin: Mapped["User"] = relationship("User", foreign_keys=[admin_id])
  ```
- **Status:** ⬜ Pending

**Task 1.2.2:** Create migration for AuditLog
- **Command:** `alembic revision --autogenerate -m "Add audit log table"`
- **Status:** ⬜ Pending

**Task 1.2.3:** Create audit logging helper
- **File:** `souvenirx-backend/app/services/audit.py` (NEW)
- **Content:**
  ```python
  import json
  from typing import Any, Dict, Optional
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.models.audit_log import AuditLog
  
  async def log_audit(
      db: AsyncSession,
      admin_id: str,
      action: str,
      resource_type: str,
      resource_id: str,
      changes: Optional[Dict[str, Any]] = None,
      ip_address: Optional[str] = None,
      user_agent: Optional[str] = None,
  ):
      """Log an admin action to the audit trail"""
      log = AuditLog(
          admin_id=admin_id,
          action=action,
          resource_type=resource_type,
          resource_id=resource_id,
          changes=json.dumps(changes) if changes else None,
          ip_address=ip_address,
          user_agent=user_agent,
      )
      db.add(log)
      await db.flush()
  ```
- **Status:** ⬜ Pending

**Task 1.2.4:** Add audit logging to customer update
- **File:** `souvenirx-backend/app/routes/admin.py` (lines 1446-1478)
- **Changes:**
  ```python
  from app.services.audit import log_audit
  
  # Before update, capture old values
  old_values = {
      "full_name": customer.full_name,
      "email": customer.email,
      "phone": customer.phone,
      "is_active": customer.is_active,
  }
  
  # ... perform updates ...
  
  # After update, log changes
  changes = {k: {"old": old_values[k], "new": getattr(customer, k)} 
             for k in old_values if old_values[k] != getattr(customer, k)}
  
  if changes:
      await log_audit(
          db=db,
          admin_id=str(admin.id),
          action="update_customer",
          resource_type="user",
          resource_id=customer_id,
          changes=changes,
          ip_address=request.client.host if request.client else None,
      )
  ```
- **Status:** ⬜ Pending

**Task 1.2.5:** Add audit logging to customer notes
- **File:** `souvenirx-backend/app/routes/admin.py`
- **Endpoints:** POST/DELETE `/admin/customers/{customer_id}/notes`
- **Status:** ⬜ Pending

**Task 1.2.6:** Add audit logging to customer tags
- **File:** `souvenirx-backend/app/routes/admin.py` (lines 1624-1643)
- **Status:** ⬜ Pending

**Task 1.2.7:** Create audit log viewing endpoint
- **File:** `souvenirx-backend/app/routes/admin.py`
- **New endpoint:**
  ```python
  @router.get("/audit-logs")
  async def list_audit_logs(
      resource_type: str | None = None,
      resource_id: str | None = None,
      admin_id: str | None = None,
      action: str | None = None,
      page: int = Query(1, ge=1),
      limit: int = Query(50, ge=1, le=100),
      admin: User = Depends(get_current_admin),
      db: AsyncSession = Depends(get_db),
  ):
      from app.models.audit_log import AuditLog
      from sqlalchemy.orm import selectinload
      
      query = select(AuditLog).options(selectinload(AuditLog.admin))
      
      if resource_type:
          query = query.where(AuditLog.resource_type == resource_type)
      if resource_id:
          query = query.where(AuditLog.resource_id == resource_id)
      if admin_id:
          query = query.where(AuditLog.admin_id == uuid.UUID(admin_id))
      if action:
          query = query.where(AuditLog.action == action)
      
      query = query.order_by(AuditLog.created_at.desc())
      result = await db.execute(query.offset((page - 1) * limit).limit(limit))
      logs = result.scalars().all()
      
      return [
          {
              "id": log.id,
              "admin_name": log.admin.full_name if log.admin else "System",
              "admin_email": log.admin.email if log.admin else None,
              "action": log.action,
              "resource_type": log.resource_type,
              "resource_id": log.resource_id,
              "changes": json.loads(log.changes) if log.changes else None,
              "ip_address": log.ip_address,
              "created_at": log.created_at.isoformat(),
          }
          for log in logs
      ]
  ```
- **Status:** ⬜ Pending

#### Frontend Tasks

**Task 1.2.8:** Create audit log viewer page
- **File:** `souvenirx-frontend/src/routes/admin.audit-logs.tsx` (NEW)
- **Features:**
  - Table with columns: timestamp, admin, action, resource, changes, IP
  - Filters: resource type, admin, action, date range
  - Pagination
  - Export to CSV
- **Status:** ⬜ Pending

**Task 1.2.9:** Add audit log link to admin sidebar
- **File:** `souvenirx-frontend/src/components/dashboard/AdminSidebar.tsx`
- **Status:** ⬜ Pending

---

### 1.3 Fix Multi-Role User Bug (Day 5)

**Task 1.3.1:** Fix customer list query
- **File:** `souvenirx-backend/app/routes/admin.py` (line 1373)
- **Change:**
  ```python
  # Before
  query = select(User).where(User.role == UserRole.customer.value)
  
  # After
  query = select(User).where(User.role.like('%customer%'))
  ```
- **Status:** ⬜ Pending

**Task 1.3.2:** Fix customer detail query
- **File:** `souvenirx-backend/app/routes/admin.py` (line 1400)
- **Same fix as above**
- **Status:** ⬜ Pending

**Task 1.3.3:** Fix customer update query
- **File:** `souvenirx-backend/app/routes/admin.py` (line 1455)
- **Same fix as above**
- **Status:** ⬜ Pending

**Task 1.3.4:** Test multi-role users
- Create test user with role="customer,affiliate"
- Verify they appear in customer list
- Verify detail view works
- Verify update works
- **Status:** ⬜ Pending

---

## Phase 2: Critical Features (Week 2)

**Priority:** 🔴 HIGH - Essential for operations  
**Estimated Time:** 5-7 days  
**Dependencies:** Phase 1 complete

### 2.1 Admin Password Reset (Days 1-2)

**Task 2.1.1:** Create password reset endpoint
- **File:** `souvenirx-backend/app/routes/admin.py`
- **New endpoint:**
  ```python
  @router.post("/customers/{customer_id}/reset-password")
  async def admin_reset_customer_password(
      customer_id: str,
      body: dict,
      request: Request,
      admin: User = Depends(get_current_admin),
      db: AsyncSession = Depends(get_db),
  ):
      """Admin resets customer password"""
      from app.services.auth import hash_password
      from app.services.audit import log_audit
      
      result = await db.execute(
          select(User).where(User.id == uuid.UUID(customer_id))
      )
      customer = result.scalar_one_or_none()
      if not customer:
          raise HTTPException(status_code=404, detail="Customer not found")
      
      new_password = body.get("new_password")
      if not new_password or len(new_password) < 8:
          raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
      
      customer.password_hash = hash_password(new_password)
      await db.flush()
      
      # Log audit
      await log_audit(
          db=db,
          admin_id=str(admin.id),
          action="reset_password",
          resource_type="user",
          resource_id=customer_id,
          ip_address=request.client.host if request.client else None,
      )
      
      # Send email notification
      try:
          from app.services.email import send_templated_email
          await send_templated_email(
              "password_reset_by_admin",
              customer.email,
              {"customer_name": customer.full_name},
              db
          )
      except Exception as e:
          print(f"Failed to send password reset email: {e}")
      
      return {"message": "Password reset successfully"}
  ```
- **Status:** ⬜ Pending

**Task 2.1.2:** Create password reset email template
- **File:** `souvenirx-backend/app/data/email_templates.py`
- **Add new template:** "password_reset_by_admin"
- **Status:** ⬜ Pending

**Task 2.1.3:** Add password reset UI
- **File:** `souvenirx-frontend/src/routes/admin.customers.tsx`
- **Changes:**
  - Add "Reset Password" button in customer detail modal
  - Create password reset modal with form
  - Password input with strength indicator
  - Confirm password field
  - Submit handler calling new endpoint
- **Status:** ⬜ Pending

**Task 2.1.4:** Add password reset to data.ts
- **File:** `souvenirx-frontend/src/lib/data.ts`
- **New function:**
  ```typescript
  export async function resetCustomerPassword(customerId: string, newPassword: string) {
    return api(`/api/admin/customers/${customerId}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ new_password: newPassword }),
    });
  }
  ```
- **Status:** ⬜ Pending

---

### 2.2 Role Management (Days 3-4)

**Task 2.2.1:** Create list all users endpoint
- **File:** `souvenirx-backend/app/routes/admin.py`
- **New endpoint:**
  ```python
  @router.get("/users")
  async def list_all_users(
      search: str | None = None,
      role_filter: str | None = None,  # "customer", "affiliate", "admin"
      page: int = Query(1, ge=1),
      limit: int = Query(50, ge=1, le=100),
      admin: User = Depends(get_current_admin),
      db: AsyncSession = Depends(get_db),
  ):
      """List all users with optional role filtering"""
      query = select(User)
      
      if search:
          query = query.where(
              or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
          )
      
      if role_filter:
          query = query.where(User.role.like(f"%{role_filter}%"))
      
      query = query.order_by(User.created_at.desc())
      result = await db.execute(query.offset((page - 1) * limit).limit(limit))
      users = result.scalars().all()
      
      return [
          {
              "id": str(u.id),
              "name": u.full_name,
              "email": u.email,
              "phone": u.phone,
              "roles": u.get_roles(),
              "active_role": u.active_role,
              "joined": u.created_at.strftime("%Y-%m-%d"),
              "is_active": u.is_active,
              "email_verified": u.email_verified,
          }
          for u in users
      ]
  ```
- **Status:** ⬜ Pending

**Task 2.2.2:** Create update user roles endpoint
- **File:** `souvenirx-backend/app/routes/admin.py`
- **New endpoint:**
  ```python
  @router.patch("/users/{user_id}/roles")
  async def update_user_roles(
      user_id: str,
      body: dict,
      request: Request,
      admin: User = Depends(get_current_admin),
      db: AsyncSession = Depends(get_db),
  ):
      """Update user roles"""
      from app.services.audit import log_audit
      
      result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
      user = result.scalar_one_or_none()
      if not user:
          raise HTTPException(status_code=404, detail="User not found")
      
      new_roles = body.get("roles", [])
      valid_roles = ["customer", "affiliate", "admin"]
      
      if not new_roles:
          raise HTTPException(status_code=400, detail="At least one role required")
      if not all(r in valid_roles for r in new_roles):
          raise HTTPException(status_code=400, detail="Invalid role")
      
      old_roles = user.get_roles()
      user.role = ",".join(new_roles)
      
      # If active_role is no longer in roles, reset it
      if user.active_role and user.active_role not in new_roles:
          user.active_role = new_roles[0]
      
      await db.flush()
      
      # Log audit
      await log_audit(
          db=db,
          admin_id=str(admin.id),
          action="update_roles",
          resource_type="user",
          resource_id=user_id,
          changes={"old_roles": old_roles, "new_roles": new_roles},
          ip_address=request.client.host if request.client else None,
      )
      
      return {"message": "Roles updated", "roles": new_roles}
  ```
- **Status:** ⬜ Pending

**Task 2.2.3:** Create user management page
- **File:** `souvenirx-frontend/src/routes/admin.users.tsx` (NEW)
- **Features:**
  - Table showing all users with roles column
  - Role filter dropdown (All, Customer, Affiliate, Admin)
  - Search by name/email
  - Click to edit roles
- **Status:** ⬜ Pending

**Task 2.2.4:** Create role editor modal
- **Component:** Role editor with checkboxes for customer/affiliate/admin
- **Validation:** At least one role must be selected
- **Status:** ⬜ Pending

**Task 2.2.5:** Add users link to admin sidebar
- **File:** `souvenirx-frontend/src/components/dashboard/AdminSidebar.tsx`
- **Status:** ⬜ Pending

---

### 2.3 User Deletion (Day 5)

**Task 2.3.1:** Create soft delete endpoint
- **File:** `souvenirx-backend/app/routes/admin.py`
- **New endpoint:**
  ```python
  @router.delete("/users/{user_id}")
  async def delete_user(
      user_id: str,
      permanent: bool = Query(False),
      request: Request,
      admin: User = Depends(get_current_admin),
      db: AsyncSession = Depends(get_db),
  ):
      """Soft delete (deactivate) or hard delete user"""
      from app.services.audit import log_audit
      
      result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
      user = result.scalar_one_or_none()
      if not user:
          raise HTTPException(status_code=404, detail="User not found")
      
      # Prevent deleting yourself
      if str(user.id) == str(admin.id):
          raise HTTPException(status_code=400, detail="Cannot delete your own account")
      
      if permanent:
          # Hard delete - requires super admin
          if not admin.has_role("admin"):
              raise HTTPException(status_code=403, detail="Super admin required for permanent deletion")
          
          await db.delete(user)
          action = "hard_delete"
      else:
          # Soft delete
          user.is_active = False
          user.email = f"deleted_{user.id}@deleted.local"
          action = "soft_delete"
      
      await db.flush()
      
      # Log audit
      await log_audit(
          db=db,
          admin_id=str(admin.id),
          action=action,
          resource_type="user",
          resource_id=user_id,
          ip_address=request.client.host if request.client else None,
      )
      
      return {"message": "User deleted"}
  ```
- **Status:** ⬜ Pending

**Task 2.3.2:** Add delete button to user management UI
- **File:** `souvenirx-frontend/src/routes/admin.users.tsx`
- **Changes:**
  - Add delete action to row actions
  - Create confirmation dialog
  - Option for soft vs hard delete (admin only)
- **Status:** ⬜ Pending

---

### 2.4 Email Verification Management (Day 6-7)

**Task 2.4.1:** Create manual verification endpoint
- **File:** `souvenirx-backend/app/routes/admin.py`
- **New endpoint:**
  ```python
  @router.post("/users/{user_id}/verify-email")
  async def admin_verify_user_email(
      user_id: str,
      request: Request,
      admin: User = Depends(get_current_admin),
      db: AsyncSession = Depends(get_db),
  ):
      """Admin manually verifies user email"""
      from app.services.audit import log_audit
      
      result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
      user = result.scalar_one_or_none()
      if not user:
          raise HTTPException(status_code=404, detail="User not found")
      
      if user.email_verified:
          raise HTTPException(status_code=400, detail="Email already verified")
      
      user.email_verified = True
      user.verification_token = None
      user.verification_token_expires_at = None
      await db.flush()
      
      # Log audit
      await log_audit(
          db=db,
          admin_id=str(admin.id),
          action="verify_email",
          resource_type="user",
          resource_id=user_id,
          ip_address=request.client.host if request.client else None,
      )
      
      return {"message": "Email verified"}
  ```
- **Status:** ⬜ Pending

**Task 2.4.2:** Add email_verified column to user list
- **File:** `souvenirx-frontend/src/routes/admin.users.tsx`
- **Changes:** Add column showing verification status with badge
- **Status:** ⬜ Pending

**Task 2.4.3:** Add verify button to user detail
- **File:** `souvenirx-frontend/src/routes/admin.customers.tsx`
- **Changes:** Add "Verify Email" button if not verified
- **Status:** ⬜ Pending

---

## Phase 3: Enhanced Features (Week 3)

**Priority:** 🟡 MEDIUM - Important for usability  
**Estimated Time:** 5-7 days  
**Dependencies:** Phase 2 complete

### 3.1 Bulk Operations (Days 1-2)

**Task 3.1.1:** Create bulk update endpoint
- **File:** `souvenirx-backend/app/routes/admin.py`
- **New endpoint:**
  ```python
  @router.post("/users/bulk-update")
  async def bulk_update_users(
      body: dict,
      request: Request,
      admin: User = Depends(get_current_admin),
      db: AsyncSession = Depends(get_db),
  ):
      """Bulk update users"""
      from app.services.audit import log_audit
      
      user_ids = [uuid.UUID(id) for id in body.get("user_ids", [])]
      action = body.get("action")  # "activate", "deactivate", "add_tag", "remove_tag"
      value = body.get("value")
      
      if not user_ids:
          raise HTTPException(status_code=400, detail="No users selected")
      
      if action == "activate":
          await db.execute(
              update(User).where(User.id.in_(user_ids)).values(is_active=True)
          )
      elif action == "deactivate":
          await db.execute(
              update(User).where(User.id.in_(user_ids)).values(is_active=False)
          )
      elif action == "add_tag":
          # More complex - need to fetch each user and append tag
          result = await db.execute(select(User).where(User.id.in_(user_ids)))
          users = result.scalars().all()
          for user in users:
              existing_tags = user.tags.split(",") if user.tags else []
              if value not in existing_tags:
                  existing_tags.append(value)
                  user.tags = ",".join(existing_tags)
      
      await db.flush()
      
      # Log audit
      await log_audit(
          db=db,
          admin_id=str(admin.id),
          action=f"bulk_{action}",
          resource_type="user",
          resource_id=",".join(str(id) for id in user_ids),
          changes={"action": action, "value": value, "count": len(user_ids)},
          ip_address=request.client.host if request.client else None,
      )
      
      return {"message": f"{len(user_ids)} users updated"}
  ```
- **Status:** ⬜ Pending

**Task 3.1.2:** Add bulk operations UI
- **File:** `souvenirx-frontend/src/routes/admin.users.tsx`
- **Changes:**
  - Add row selection checkboxes
  - Add bulk action dropdown (Activate, Deactivate, Add Tag, Delete)
  - Add "Apply to Selected" button
  - Show count of selected users
- **Status:** ⬜ Pending

---

### 3.2 Email Verification Enforcement (Days 3-4)

**Task 3.2.1:** Create require_verified_email middleware
- **File:** `souvenirx-backend/app/middleware/auth.py`
- **New function:**
  ```python
  async def require_verified_email(user: User = Depends(get_current_user)) -> User:
      """Require user to have verified email"""
      if not user.email_verified:
          raise HTTPException(
              status_code=403,
              detail="Please verify your email address to continue. Check your inbox for the verification link."
          )
      return user
  ```
- **Status:** ⬜ Pending

**Task 3.2.2:** Apply to checkout endpoint
- **File:** `souvenirx-backend/app/routes/orders.py`
- **Change:** Replace `Depends(get_current_user)` with `Depends(require_verified_email)`
- **Status:** ⬜ Pending

**Task 3.2.3:** Apply to order creation endpoint
- **File:** `souvenirx-backend/app/routes/orders.py`
- **Status:** ⬜ Pending

**Task 3.2.4:** Add verification banner to frontend
- **File:** `souvenirx-frontend/src/components/site/Header.tsx`
- **Changes:**
  - Check if user is logged in and email not verified
  - Show banner: "Please verify your email. Didn't receive it? [Resend]"
- **Status:** ⬜ Pending

**Task 3.2.5:** Add resend verification to user profile
- **File:** `souvenirx-frontend/src/routes/dashboard.tsx`
- **Changes:**
  - Show verification status
  - Add "Resend Verification Email" button
- **Status:** ⬜ Pending

---

### 3.3 Input Validation & Security (Day 5)

**Task 3.3.1:** Add input validation to customer update
- **File:** `souvenirx-backend/app/routes/admin.py` (lines 1446-1478)
- **Changes:**
  ```python
  import re
  
  if "full_name" in body:
      if not body["full_name"] or len(body["full_name"]) < 2:
          raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
      customer.full_name = body["full_name"]
  
  if "email" in body:
      email = body["email"]
      if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
          raise HTTPException(status_code=400, detail="Invalid email format")
      # Check uniqueness...
  
  if "phone" in body:
      phone = body["phone"]
      if phone and not re.match(r"^\+?[0-9\s\-()]{10,20}$", phone):
          raise HTTPException(status_code=400, detail="Invalid phone format")
      customer.phone = phone
  ```
- **Status:** ⬜ Pending

**Task 3.3.2:** Add length limit to customer notes
- **File:** `souvenirx-backend/app/routes/admin.py` (lines 1512-1541)
- **Changes:**
  ```python
  note_text = body.get("note")
  if not note_text:
      raise HTTPException(status_code=400, detail="Note text is required")
  if len(note_text) > 1000:
      raise HTTPException(status_code=400, detail="Note must be 1000 characters or less")
  ```
- **Status:** ⬜ Pending

**Task 3.3.3:** Add rate limiting to admin endpoints
- **File:** `souvenirx-backend/app/routes/admin.py`
- **Add to all POST/PATCH/DELETE endpoints:**
  ```python
  client_ip = request.client.host if request.client else "unknown"
  if not await check_rate_limit(f"rl:admin:{admin.id}:{client_ip}", 100, 60):
      raise HTTPException(status_code=429, detail="Too many requests")
  ```
- **Status:** ⬜ Pending

---

## Phase 4: Performance Optimization (Week 4)

**Priority:** 🟢 LOW - Nice to have  
**Estimated Time:** 5-7 days  
**Dependencies:** Phase 3 complete

### 4.1 Query Optimization (Days 1-2)

**Task 4.1.1:** Optimize customer list query
- **File:** `souvenirx-backend/app/routes/admin.py` (lines 1365-1388)
- **Changes:**
  ```python
  # Use JOIN to get order stats in single query
  from sqlalchemy import func, case
  
  query = (
      select(
          User,
          func.count(Order.id).label("order_count"),
          func.coalesce(func.sum(
              case((Order.payment_status == PaymentStatus.success.value, Order.total), else_=0)
          ), 0).label("total_spent")
      )
      .outerjoin(Order, User.id == Order.user_id)
      .where(User.role.like('%customer%'))
      .group_by(User.id)
  )
  ```
- **Status:** ⬜ Pending

**Task 4.1.2:** Optimize LTV calculation
- **File:** `souvenirx-backend/app/routes/admin.py` (lines 1569-1621)
- **Changes:**
  ```python
  # Use aggregation instead of loading all orders
  from sqlalchemy import func, literal
  
  stats = await db.execute(
      select(
          func.count(Order.id).label("total_orders"),
          func.sum(Order.total).label("total_spent"),
          func.min(Order.created_at).label("first_order"),
          func.max(Order.created_at).label("last_order"),
      )
      .where(Order.user_id == customer_uuid, Order.payment_status == PaymentStatus.success.value)
  )
  result = stats.one()
  ```
- **Status:** ⬜ Pending

**Task 4.1.3:** Add caching to customer detail
- **File:** `souvenirx-backend/app/routes/admin.py`
- **Changes:**
  ```python
  from app.redis import get_redis
  import json
  
  # Try cache first
  redis = await get_redis()
  cache_key = f"customer_detail:{customer_id}"
  cached = await redis.get(cache_key)
  if cached:
      return json.loads(cached)
  
  # ... fetch from DB ...
  
  # Cache for 5 minutes
  await redis.setex(cache_key, 300, json.dumps(result))
  ```
- **Status:** ⬜ Pending

---

### 4.2 CSV Export Optimization (Day 3)

**Task 4.2.1:** Implement streaming CSV export
- **File:** `souvenirx-backend/app/routes/admin.py` (lines 1646-1664+)
- **Changes:**
  ```python
  from fastapi.responses import StreamingResponse
  import csv
  from io import StringIO
  
  @router.get("/users/export")
  async def export_users_csv(
      admin: User = Depends(get_current_admin),
      db: AsyncSession = Depends(get_db),
  ):
      """Stream CSV export for large datasets"""
      async def generate():
          output = StringIO()
          writer = csv.writer(output)
          
          # Write header
          writer.writerow(["ID", "Name", "Email", "Phone", "Roles", "Joined", "Active", "Verified"])
          yield output.getvalue()
          output.truncate(0)
          output.seek(0)
          
          # Stream users in batches
          batch_size = 1000
          offset = 0
          while True:
              result = await db.execute(
                  select(User).order_by(User.created_at.desc()).offset(offset).limit(batch_size)
              )
              users = result.scalars().all()
              if not users:
                  break
              
              for user in users:
                  writer.writerow([
                      str(user.id), user.full_name, user.email, user.phone or "",
                      user.role, user.created_at.strftime("%Y-%m-%d"),
                      "Yes" if user.is_active else "No",
                      "Yes" if user.email_verified else "No",
                  ])
              
              yield output.getvalue()
              output.truncate(0)
              output.seek(0)
              offset += batch_size
      
      return StreamingResponse(
          generate(),
          media_type="text/csv",
          headers={"Content-Disposition": "attachment; filename=users_export.csv"}
      )
  ```
- **Status:** ⬜ Pending

---

### 4.3 Advanced Filtering (Days 4-5)

**Task 4.3.1:** Create advanced filter endpoint
- **File:** `souvenirx-backend/app/routes/admin.py`
- **Enhance list_all_users with filters:**
  ```python
  @router.get("/users")
  async def list_all_users(
      search: str | None = None,
      role_filter: str | None = None,
      is_active: bool | None = None,
      email_verified: bool | None = None,
      joined_after: str | None = None,  # ISO date
      joined_before: str | None = None,
      min_orders: int | None = None,
      max_orders: int | None = None,
      min_spent: int | None = None,
      max_spent: int | None = None,
      tags: str | None = None,  # Comma-separated
      page: int = Query(1, ge=1),
      limit: int = Query(50, ge=1, le=100),
      admin: User = Depends(get_current_admin),
      db: AsyncSession = Depends(get_db),
  ):
      # Build complex query with all filters
      # ...
  ```
- **Status:** ⬜ Pending

**Task 4.3.2:** Create advanced filter UI
- **File:** `souvenirx-frontend/src/routes/admin.users.tsx`
- **Component:** FilterBuilder with:
  - Date range picker
  - Order count range slider
  - Spending range slider
  - Tag multi-select
  - Verification status toggle
  - Active status toggle
- **Status:** ⬜ Pending

---

### 4.4 Optional Enhancements (Days 6-7)

**Task 4.4.1:** Add customer impersonation (optional)
- **File:** `souvenirx-backend/app/routes/admin.py`
- **See audit report for implementation**
- **Status:** ⬜ Pending

**Task 4.4.2:** Add 2FA for admin accounts (optional)
- **Files:** Multiple (auth flow, models, UI)
- **Status:** ⬜ Pending

**Task 4.4.3:** Add IP whitelisting (optional)
- **File:** `souvenirx-backend/app/middleware/auth.py`
- **Status:** ⬜ Pending

---

## Phase 5: Testing & Documentation (Week 4+)

**Priority:** ✅ REQUIRED - Must be done before deployment  
**Estimated Time:** 3-5 days  
**Dependencies:** All features complete

### 5.1 Automated Testing (Days 1-2)

**Task 5.1.1:** Email verification tests
- **File:** `souvenirx-backend/tests/test_email_verification.py` (NEW)
- **Test cases:**
  - Valid token verification
  - Expired token rejection
  - Already verified email
  - Invalid token
  - Rate limiting
  - Token resend
- **Status:** ⬜ Pending

**Task 5.1.2:** User management tests
- **File:** `souvenirx-backend/tests/test_admin_users.py` (NEW)
- **Test cases:**
  - List users with filters
  - Update customer info
  - Reset password
  - Update roles
  - Delete user (soft/hard)
  - Bulk operations
- **Status:** ⬜ Pending

**Task 5.1.3:** Audit logging tests
- **File:** `souvenirx-backend/tests/test_audit_log.py` (NEW)
- **Test cases:**
  - Audit log creation
  - Audit log retrieval
  - Audit log filtering
- **Status:** ⬜ Pending

---

### 5.2 Documentation (Days 3-4)

**Task 5.2.1:** API documentation
- **File:** `souvenirx-backend/docs/API.md`
- **Document all new endpoints with:**
  - Request/response schemas
  - Authentication requirements
  - Rate limits
  - Example requests
- **Status:** ⬜ Pending

**Task 5.2.2:** Admin user guide
- **File:** `souvenirx-backend/docs/ADMIN_GUIDE.md` (NEW)
- **Sections:**
  - User management overview
  - How to reset passwords
  - How to manage roles
  - How to use audit logs
  - How to perform bulk operations
  - Best practices
- **Status:** ⬜ Pending

**Task 5.2.3:** Update README
- **File:** `souvenirx-backend/README.md`
- **Add sections:**
  - Email verification flow
  - Admin features
  - Security features
- **Status:** ⬜ Pending

---

### 5.3 Deployment Preparation (Day 5)

**Task 5.3.1:** Run all migrations
- **Commands:**
  ```bash
  alembic upgrade head
  ```
- **Status:** ⬜ Pending

**Task 5.3.2:** Seed email templates
- **Ensure all new templates are in database**
- **Status:** ⬜ Pending

**Task 5.3.3:** Update environment variables
- **Add any new config:**
  - Rate limit settings
  - Cache TTL
  - CSV export batch size
- **Status:** ⬜ Pending

**Task 5.3.4:** Security audit
- **Checklist:**
  - [ ] All endpoints have proper auth
  - [ ] Rate limiting enabled
  - [ ] Input validation on all forms
  - [ ] Audit logging on all sensitive operations
  - [ ] CSRF protection enabled
  - [ ] SQL injection prevention (using ORM)
  - [ ] XSS prevention (React escapes by default)
- **Status:** ⬜ Pending

---

## Summary

### Total Tasks: 51

**By Priority:**
- 🔴 Critical: 20 tasks (Phases 1-2)
- 🟡 Medium: 16 tasks (Phase 3)
- 🟢 Low: 10 tasks (Phase 4)
- ✅ Required: 5 tasks (Phase 5)

**By Type:**
- Backend: 30 tasks
- Frontend: 12 tasks
- Testing: 3 tasks
- Documentation: 3 tasks
- DevOps: 3 tasks

**Estimated Timeline:**
- Week 1: Critical security fixes
- Week 2: Critical features
- Week 3: Enhanced features
- Week 4: Performance & testing
- Week 4+: Documentation & deployment

**Risk Areas:**
- Database migrations (test in staging first)
- Multi-role user query changes (affects existing data)
- CSV export streaming (test with large datasets)
- Audit log storage (monitor disk usage)

**Success Criteria:**
- [ ] All verification tokens expire after 24 hours
- [ ] All admin actions are logged
- [ ] Multi-role users work correctly
- [ ] Admins can reset passwords
- [ ] Admins can manage roles
- [ ] Bulk operations work efficiently
- [ ] All tests pass
- [ ] Documentation complete
- [ ] Security audit passed
