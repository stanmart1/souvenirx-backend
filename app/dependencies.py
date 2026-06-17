"""Dependency re-exports for backwards compatibility with app.routers"""
from app.middleware.auth import (
    get_current_user,
    get_current_admin as require_admin,
    get_optional_user,
    get_current_admin,
)

__all__ = [
    "get_current_user",
    "require_admin",
    "get_optional_user",
    "get_current_admin",
]
