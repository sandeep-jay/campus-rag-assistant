"""Gate developer-only HTTP routes."""

from fastapi import HTTPException, status

from backend.app.core.config_manager import settings


def require_dev_api_routes() -> None:
    """Raise 404 when developer diagnostics are disabled (e.g. production)."""
    if not getattr(settings, 'ENABLE_DEV_API_ROUTES', False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not Found')
