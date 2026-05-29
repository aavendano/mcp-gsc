"""Service account authentication for Google Search Console."""

from __future__ import annotations

import logging
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from gsc_mcp.config import Settings, load_settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/webmasters"]

_settings: Settings | None = None
_service: Any | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reset_auth_cache() -> None:
    """Clear cached settings and service (for tests)."""
    global _settings, _service
    _settings = None
    _service = None


def configure(settings: Settings) -> None:
    global _settings, _service
    _settings = settings
    _service = None


def get_gsc_service(force_new: bool = False) -> Any:
    """Return an authorized Search Console API service (service account only)."""
    global _service
    settings = get_settings()

    if not settings.skip_oauth:
        logger.warning(
            "GSC_SKIP_OAUTH is not true; OAuth is disabled in this private server. "
            "Set GSC_SKIP_OAUTH=true and use GSC_CREDENTIALS_PATH."
        )

    cred_path = settings.gsc_credentials_path
    if not cred_path:
        raise FileNotFoundError(
            "GSC_CREDENTIALS_PATH is required. Set it to the absolute path of your "
            "service account JSON key file."
        )
    if not __import__("os").path.exists(cred_path):
        raise FileNotFoundError(
            f"GSC_CREDENTIALS_PATH is set to {cred_path!r} but the file does not exist."
        )

    if _service is not None and not force_new:
        return _service

    creds = service_account.Credentials.from_service_account_file(
        cred_path, scopes=SCOPES
    )
    _service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    return _service
