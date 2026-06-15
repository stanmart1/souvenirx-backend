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
    role: str  # Comma-separated roles
    active_role: str | None  # Current active role
    email_verified: bool = False

    model_config = {"from_attributes": True}
    
    @property
    def roles(self) -> list[str]:
        """Get list of roles"""
        return [r.strip() for r in self.role.split(",") if r.strip()]


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


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
