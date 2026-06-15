"""
Public configuration endpoint for mobile app runtime config.

Returns public keys and OAuth client IDs that the mobile app needs
to initialize payment SDKs and social login.

SECURITY: Only returns PUBLIC keys — never secrets or private keys.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/config", tags=["config"])


class ConfigResponse(BaseModel):
    """Public configuration for mobile app."""
    google_web_client_id: str
    paystack_public_key: str
    flutterwave_public_key: str


@router.get("", response_model=ConfigResponse)
async def get_config():
    """
    Get public configuration for mobile app.
    
    Returns OAuth client IDs and payment gateway public keys.
    These are safe to expose to the mobile app as they are public keys only.
    
    Returns:
        ConfigResponse: Public keys and client IDs
    """
    return ConfigResponse(
        google_web_client_id=settings.google_client_id,
        paystack_public_key=settings.paystack_public_key,
        flutterwave_public_key=settings.flutterwave_public_key,
    )
