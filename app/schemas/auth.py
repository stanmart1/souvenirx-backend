import uuid
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    roles: list[str] = []
    active_role: str | None = None
    email_verified: bool = False
    avatar_url: str | None = None
    loyalty_points: int = 0
    created_by_admin: bool = False

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


class AdminCreateUserRequest(BaseModel):
    """Body for POST /admin/users — creates a user with OTP bypass."""
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    roles: list[str] = ["customer"]  # subset of ["customer", "affiliate", "admin"]
    send_welcome_email: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class VerifyOtpRequest(BaseModel):
    """Mobile-app OTP verification body (6-digit numeric code)."""
    email: EmailStr
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class AddressCreate(BaseModel):
    label: str = "Home"
    full_name: str
    phone: str
    address: str
    city: str
    state: str
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: str | None = None
    full_name: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    is_default: bool | None = None
