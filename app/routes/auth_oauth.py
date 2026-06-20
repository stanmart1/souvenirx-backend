"""
Google OAuth 2.0 authentication flow.

Configuration required in .env:
  GOOGLE_CLIENT_ID=<your-client-id>
  GOOGLE_CLIENT_SECRET=<your-client-secret>

In Google Cloud Console:
  Authorized redirect URIs: {BACKEND_URL}/api/auth/google/callback
"""
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.auth import create_access_token, create_refresh_token

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPES = "openid email profile"


def _redirect_uri() -> str:
    return f"{settings.backend_url}/api/auth/google/callback"


@router.get("/google", summary="Redirect to Google OAuth consent screen")
async def google_login():
    """
    Redirects the browser to Google's OAuth 2.0 consent screen.
    Requires GOOGLE_CLIENT_ID to be configured.
    """
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = GOOGLE_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=url)


@router.get("/google/callback", summary="Handle Google OAuth callback")
async def google_callback(
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchanges the Google authorization code for an access token,
    fetches user info, creates or finds the SouvenirX user, and
    redirects back to the frontend with JWT tokens in the URL hash.
    """
    frontend_url = settings.frontend_url.rstrip("/")

    if error or not code:
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_denied")

    if not settings.google_client_id or not settings.google_client_secret:
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_not_configured")

    async with httpx.AsyncClient() as client:
        # Exchange authorization code for tokens
        try:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": _redirect_uri(),
                    "grant_type": "authorization_code",
                },
                timeout=15,
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
        except Exception:
            return RedirectResponse(url=f"{frontend_url}/login?error=token_exchange_failed")

        google_access_token = token_data.get("access_token")
        if not google_access_token:
            return RedirectResponse(url=f"{frontend_url}/login?error=no_access_token")

        # Fetch user profile from Google
        try:
            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
                timeout=10,
            )
            userinfo_resp.raise_for_status()
            userinfo = userinfo_resp.json()
        except Exception:
            return RedirectResponse(url=f"{frontend_url}/login?error=userinfo_failed")

    email = userinfo.get("email")
    name = userinfo.get("name") or userinfo.get("given_name") or "Google User"
    google_id = userinfo.get("id")

    if not email:
        return RedirectResponse(url=f"{frontend_url}/login?error=no_email")

    # Find existing user or create new one
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=uuid.uuid4(),
            email=email,
            full_name=name,
            # No password set for OAuth users — they can always set one via "forgot password"
            hashed_password="",
            is_active=True,
            email_verified=True,  # Google has verified their email
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        from app.services.rbac import assign_roles
        await assign_roles(db, user, ["customer"])

    # Issue SouvenirX JWT tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Redirect to frontend with tokens in URL fragment (not query params — not logged in history)
    redirect_url = (
        f"{frontend_url}/oauth/callback"
        f"#access_token={access_token}"
        f"&refresh_token={refresh_token}"
        f"&user_id={user.id}"
    )
    return RedirectResponse(url=redirect_url)
