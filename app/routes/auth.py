import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, Address
from app.models.guest_session import GuestSession
from app.models.cart import CartItem
from app.models.order import Order
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    UserResponse, UpdateProfileRequest, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest, VerifyOtpRequest,
    AddressCreate, AddressUpdate,
)
from app.services.auth import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, create_reset_token, create_guest_token, decode_token,
)
from app.middleware.auth import get_current_user
from app.redis import check_rate_limit

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Customer registration - creates user with 'customer' role"""
    import secrets
    from datetime import timedelta, timezone

    def _generate_otp() -> str:
        """6-digit numeric OTP for the mobile verification flow."""
        return f"{secrets.randbelow(1_000_000):06d}"

    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:register:{client_ip}", 5, 300):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please wait.")
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate URL token (web click-link) + numeric OTP (mobile entry).
    verification_token = secrets.token_urlsafe(32)
    otp = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        phone=req.phone,
        role="customer",  # Explicitly set role
        email_verified=False,
        verification_token=verification_token,
        verification_token_expires_at=expires_at,
        email_otp=otp,
        email_otp_expires_at=expires_at,
        # Self-signup users are NOT admin-created; OTP verification required.
        created_by_admin=False,
    )
    db.add(user)
    await db.flush()

    from app.services.rbac import sync_user_roles_from_legacy
    await sync_user_roles_from_legacy(db, user)

    from app.routes.loyalty import award_points, get_rule_value
    signup_bonus = await get_rule_value(db, "signup_bonus")
    if signup_bonus and signup_bonus > 0:
        await award_points(db, user.id, signup_bonus, "signup",
                           f"Welcome bonus: {signup_bonus} points for signing up")

    # Send verification email with both click-link and numeric OTP.
    try:
        from app.services.email import send_verification_email
        await send_verification_email(user.email, user.full_name, verification_token, db, otp=otp)
    except Exception as e:
        print(f"Failed to send verification email: {e}")

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/affiliate/register", response_model=TokenResponse)
async def affiliate_register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Affiliate registration - creates user with 'affiliate' role"""
    import secrets
    from datetime import timedelta, timezone
    from app.models.affiliate import Affiliate

    def _generate_otp() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:affiliate_register:{client_ip}", 5, 300):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please wait.")
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    verification_token = secrets.token_urlsafe(32)
    otp = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        phone=req.phone,
        role="affiliate",  # Set role as affiliate
        email_verified=False,
        verification_token=verification_token,
        verification_token_expires_at=expires_at,
        email_otp=otp,
        email_otp_expires_at=expires_at,
        created_by_admin=False,
    )
    db.add(user)
    await db.flush()

    # Create affiliate record
    affiliate = Affiliate(
        user_id=user.id,
        referral_code=secrets.token_urlsafe(8).upper()[:8],
        commission_rate=10.0,  # Default 10% commission
    )
    db.add(affiliate)
    await db.flush()

    from app.services.rbac import sync_user_roles_from_legacy
    await sync_user_roles_from_legacy(db, user)

    # Send verification email with both click-link and numeric OTP.
    try:
        from app.services.email import send_verification_email
        await send_verification_email(user.email, user.full_name, verification_token, db, otp=otp)
    except Exception as e:
        print(f"Failed to send verification email: {e}")

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/verify-email")
async def verify_email(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Verify user email with verification token"""
    from datetime import timezone
    
    # Rate limiting: 5 attempts per 5 minutes per IP
    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:verify:{client_ip}", 5, 300):
        raise HTTPException(status_code=429, detail="Too many verification attempts. Please wait a few minutes.")
    
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification link. Please request a new one.")
    
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified. You can proceed to login.")
    
    # Check if token has expired
    if user.verification_token_expires_at and user.verification_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification link has expired. Please request a new one from your profile.")
    
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    user.email_otp = None
    user.email_otp_expires_at = None
    await db.commit()

    # Send welcome email now that the address is confirmed
    try:
        from app.services.email import send_welcome_email
        await send_welcome_email(user.email, user.full_name, db)
    except Exception as e:
        print(f"Failed to send welcome email: {e}")

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Resend verification email (new URL token + new numeric OTP)."""
    import secrets
    from datetime import timedelta, timezone

    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    verification_token = secrets.token_urlsafe(32)
    otp = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    user.verification_token = verification_token
    user.verification_token_expires_at = expires_at
    user.email_otp = otp
    user.email_otp_expires_at = expires_at
    await db.commit()

    try:
        from app.services.email import send_verification_email
        await send_verification_email(user.email, user.full_name, verification_token, db, otp=otp)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send verification email")

    return {"message": "Verification email sent"}


@router.post("/verify-otp")
async def verify_otp(
    req: VerifyOtpRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify a user's email with a 6-digit numeric OTP.

    Used by the mobile app's EmailVerificationScreen. The web app uses
    :func:`verify_email` with a URL token instead. Both paths set
    ``email_verified=True`` and clear the outstanding credentials.
    """
    from datetime import timezone

    # Rate limit: 5 OTP attempts per 5 minutes per IP.
    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:verify_otp:{client_ip}", 5, 300):
        raise HTTPException(
            status_code=429,
            detail="Too many verification attempts. Please wait a few minutes.",
        )

    if not req.otp.isdigit() or len(req.otp) != 6:
        raise HTTPException(status_code=400, detail="OTP must be a 6-digit number")

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="No pending verification for this email")

    if user.email_verified:
        return {"message": "Email already verified"}

    if not user.email_otp or not user.email_otp_expires_at:
        raise HTTPException(
            status_code=400,
            detail="No OTP on file. Please request a new verification email.",
        )

    if user.email_otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="OTP expired. Please request a new one from the app.",
        )

    if user.email_otp != req.otp:
        raise HTTPException(status_code=400, detail="Incorrect OTP. Please try again.")

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    user.email_otp = None
    user.email_otp_expires_at = None
    await db.commit()

    try:
        from app.services.email import send_welcome_email
        await send_welcome_email(user.email, user.full_name, db)
    except Exception as e:
        print(f"Failed to send welcome email: {e}")

    return {"message": "Email verified successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Unified customer/affiliate login.

    Accepts users with either the 'customer' or 'affiliate' role. Customers
    with both roles default to the customer dashboard; affiliates without a
    customer role land in the affiliate dashboard. Admin users must use the
    dedicated admin login endpoint.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:login:{client_ip}", 10, 300):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait.")
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.has_role("admin") and not user.has_role("customer") and not user.has_role("affiliate"):
        raise HTTPException(status_code=403, detail="Please use the admin login page for your account type")

    if not user.has_role("customer") and not user.has_role("affiliate"):
        raise HTTPException(status_code=403, detail="Please use the appropriate login page for your account type")

    # Default active role: customer first, then affiliate, then first available role
    user.active_role = "customer" if user.has_role("customer") else ("affiliate" if user.has_role("affiliate") else user.get_roles()[0])
    await db.flush()

    from app.services.rbac import sync_user_roles_from_legacy
    await sync_user_roles_from_legacy(db, user)

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/affiliate/login", response_model=TokenResponse)
async def affiliate_login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Affiliate login - allows users with 'affiliate' role (can have multiple roles)"""
    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:affiliate_login:{client_ip}", 10, 300):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait.")
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user has affiliate role
    if not user.has_role("affiliate"):
        raise HTTPException(status_code=403, detail="This login is for affiliates only. Please use the customer login page.")
    
    # Set active role to affiliate
    user.active_role = "affiliate"
    await db.flush()

    from app.services.rbac import sync_user_roles_from_legacy
    await sync_user_roles_from_legacy(db, user)

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Admin login - allows users with 'admin' role (can have multiple roles)"""
    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:admin_login:{client_ip}", 10, 300):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait.")
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user has admin role
    if not user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Set active role to admin
    user.active_role = "admin"
    await db.flush()

    from app.services.rbac import sync_user_roles_from_legacy
    await sync_user_roles_from_legacy(db, user)

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.get("/me/permissions")
async def get_me_permissions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's roles and effective permissions from the RBAC tables.

    This is used by the frontend to render navigation and guards based on
    fine-grained permissions instead of coarse role booleans.
    """
    from app.middleware.permissions import user_has_permission
    from app.models.rbac import Permission, Role, role_permissions

    # Get active role names from the new RBAC tables
    role_rows = await db.execute(
        select(Role.name)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == user.id, Role.is_active.is_(True))
    )
    rbac_roles = sorted(role_rows.scalars().all())

    # Get effective permissions from the new RBAC tables
    permission_rows = await db.execute(
        select(Permission.resource, Permission.action)
        .join(role_permissions, Permission.id == role_permissions.c.permission_id)
        .join(user_roles, role_permissions.c.role_id == user_roles.c.role_id)
        .join(Role, role_permissions.c.role_id == Role.id)
        .where(
            user_roles.c.user_id == user.id,
            Role.is_active.is_(True),
        )
        .distinct()
    )
    permissions = sorted({f"{r}:{a}" for r, a in permission_rows.all()})

    # Include legacy role string for backwards compatibility during transition.
    return {
        "role": user.role,
        "active_role": user.active_role,
        "roles": rbac_roles,
        "permissions": permissions,
        "is_superuser": await user_has_permission(user, "*:*", db),
    }


@router.put("/me", response_model=UserResponse)
async def update_me(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.full_name is not None:
        user.full_name = req.full_name
    if req.phone is not None:
        user.phone = req.phone
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url
    await db.flush()
    return user


@router.put("/me/fcm-token")
async def update_fcm_token(
    req: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register or refresh the FCM device token for the authenticated user."""
    token = req.get("fcm_token")
    if not token:
        raise HTTPException(status_code=400, detail="fcm_token is required")
    user.fcm_token = token
    await db.flush()
    return {"message": "FCM token updated"}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(req.new_password)
    await db.flush()
    return {"message": "Password updated"}


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:forgot:{client_ip}", 3, 300):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if user and user.is_active:
        try:
            from app.services.email import send_password_reset_email
            token = create_reset_token({"sub": str(user.id)})
            await send_password_reset_email(user.email, user.full_name, token)
        except Exception:
            pass

    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.token)
    if not payload or payload.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = hash_password(req.new_password)
    await db.flush()
    return {"message": "Password has been reset successfully"}


# --- Addresses ---
@router.get("/addresses")
async def list_addresses(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Address).where(Address.user_id == user.id).order_by(Address.is_default.desc(), Address.id))
    addresses = result.scalars().all()
    return [
        {
            "id": a.id, "label": a.label, "full_name": a.full_name, "phone": a.phone,
            "address": a.address, "city": a.city, "state": a.state, "is_default": a.is_default,
        }
        for a in addresses
    ]


@router.post("/addresses")
async def create_address(
    req: AddressCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.is_default:
        result = await db.execute(select(Address).where(Address.user_id == user.id, Address.is_default == True))
        for existing in result.scalars().all():
            existing.is_default = False

    addr = Address(
        user_id=user.id, label=req.label, full_name=req.full_name,
        phone=req.phone, address=req.address, city=req.city,
        state=req.state, is_default=req.is_default,
    )
    db.add(addr)
    await db.flush()
    return {"id": addr.id, "message": "Address added"}


@router.put("/addresses/{address_id}")
async def update_address(
    address_id: int,
    req: AddressUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Address).where(Address.id == address_id, Address.user_id == user.id))
    addr = result.scalar_one_or_none()
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")

    # Validate state (Nigeria states)
    NIGERIA_STATES = [
        "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno",
        "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "Gombe", "Imo", "Jigawa",
        "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa",
        "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba",
        "Yobe", "Zamfara", "FCT"
    ]
    
    if req.state and req.state not in NIGERIA_STATES:
        raise HTTPException(status_code=400, detail="Invalid Nigerian state")

    if req.is_default:
        others = await db.execute(select(Address).where(Address.user_id == user.id, Address.id != address_id, Address.is_default == True))
        for existing in others.scalars().all():
            existing.is_default = False

    for field in ["label", "full_name", "phone", "address", "city", "state", "is_default"]:
        value = getattr(req, field)
        if value is not None:
            setattr(addr, field, value)

    await db.flush()
    return {"message": "Address updated"}


@router.delete("/addresses/{address_id}")
async def delete_address(
    address_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Address).where(Address.id == address_id, Address.user_id == user.id))
    addr = result.scalar_one_or_none()
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")

    await db.delete(addr)
    await db.flush()
    return {"message": "Address deleted"}


# --- Guest Session Management ---
@router.post("/guest/start", response_model=TokenResponse)
async def start_guest_session(
    req: RegisterRequest,  # Reuse RegisterRequest for email/name
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Start a guest checkout session."""
    client_ip = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"rl:guest:{client_ip}", 10, 300):
        raise HTTPException(status_code=429, detail="Too many guest session attempts. Please wait.")
    
    # Check if email already exists as a user
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered. Please login instead.")
    
    # Check if guest session already exists for this email
    result = await db.execute(select(GuestSession).where(GuestSession.email == req.email))
    existing_guest = result.scalar_one_or_none()
    if existing_guest and existing_guest.converted_to_user_id is None:
        # Return existing guest session
        return TokenResponse(
            access_token=create_guest_token({"sub": str(existing_guest.id)}),
            refresh_token=create_guest_token({"sub": str(existing_guest.id)}),
        )
    
    # Create new guest session
    guest = GuestSession(
        email=req.email,
        full_name=req.full_name,
        phone=req.phone,
    )
    db.add(guest)
    await db.flush()
    
    return TokenResponse(
        access_token=create_guest_token({"sub": str(guest.id)}),
        refresh_token=create_guest_token({"sub": str(guest.id)}),
    )


@router.post("/guest/convert", response_model=TokenResponse)
async def convert_guest_to_user(
    req: RegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert a guest session to a registered user account."""
    # Find guest session by email
    result = await db.execute(select(GuestSession).where(GuestSession.email == req.email))
    guest = result.scalar_one_or_none()
    
    if not guest:
        raise HTTPException(status_code=404, detail="Guest session not found")
    
    if guest.converted_to_user_id:
        raise HTTPException(status_code=400, detail="Guest session already converted")
    
    # Update guest with conversion info
    guest.converted_to_user_id = user.id
    guest.converted_at = datetime.now()

    # Merge guest cart into user cart
    if guest.cart_data:
        try:
            items = json.loads(guest.cart_data)
            if isinstance(items, list):
                existing = await db.execute(
                    select(CartItem).where(CartItem.user_id == user.id)
                )
                existing_keys = {
                    (str(c.product_id), str(c.variant_id or ""))
                    for c in existing.scalars().all()
                }
                for item in items:
                    pid = item.get("product_id") or item.get("productId")
                    if not pid:
                        continue
                    vid = item.get("variant_id") or item.get("variantId")
                    key = (str(pid), str(vid or ""))
                    if key in existing_keys:
                        continue
                    db.add(CartItem(
                        user_id=user.id,
                        product_id=uuid.UUID(str(pid)),
                        variant_id=uuid.UUID(str(vid)) if vid else None,
                        qty=item.get("qty", 1),
                        customization=item.get("customization"),
                        logo_url=item.get("logo_url") or item.get("logoUrl"),
                    ))
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # Transfer guest orders to the new user account
    await db.execute(
        update(Order)
        .where(Order.email == guest.email, Order.user_id.is_(None))
        .values(user_id=user.id)
    )
    
    await db.flush()
    
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.get("/guest/orders")
async def lookup_guest_orders(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """Lookup orders for a guest by email (for order tracking)."""
    from app.models.order import Order
    
    result = await db.execute(
        select(Order)
        .where(Order.email == email)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    
    return [
        {
            "order_number": o.order_number,
            "total": o.total,
            "status": o.status,
            "created_at": o.created_at.isoformat(),
        }
        for o in orders
    ]


@router.post("/switch-role")
async def switch_role(
    role: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Switch the active role for the current user"""
    # Validate that user has this role
    if not user.has_role(role):
        raise HTTPException(
            status_code=403, 
            detail=f"You do not have the '{role}' role. Available roles: {', '.join(user.get_roles())}"
        )
    
    # Update active role
    user.active_role = role
    await db.flush()

    from app.services.rbac import sync_user_roles_from_legacy
    await sync_user_roles_from_legacy(db, user)

    return {
        "message": f"Switched to {role} role",
        "active_role": role,
        "available_roles": user.get_roles()
    }
