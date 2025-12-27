"""Thin web layer for SSO downloads and previews."""

from .api import app, create_app

__all__ = ["app", "create_app"]
