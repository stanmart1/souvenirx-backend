"""
Security-headers middleware.

Adds a standard set of HTTP security headers to every response.
Mount this in main.py with:

    from app.middleware.security import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_CSP = (
    "default-src 'self'; "
    "img-src 'self' data: https:; "
    "script-src 'self' 'unsafe-inline' https://js.paystack.co https://checkout.flutterwave.com https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "font-src 'self' data: https:; "
    "connect-src 'self' https://api.paystack.co https://api.flutterwave.com; "
    "frame-src https://js.paystack.co https://checkout.flutterwave.com"
)

_HSTS = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = _CSP

        # Only set HSTS over HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = _HSTS

        return response
