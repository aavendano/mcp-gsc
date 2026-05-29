"""Environment-based configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _expand_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return os.path.expandvars(os.path.expanduser(path))


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in ("true", "1", "yes")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    gsc_credentials_path: Optional[str]
    skip_oauth: bool
    allow_destructive: bool
    data_state: str
    primary_gsc_property: Optional[str]
    secondary_gsc_property: Optional[str]
    target_path_prefix: Optional[str]
    default_days: int
    min_impressions: int
    max_rows: int
    mcp_transport: str
    mcp_host: str
    mcp_port: int

    @property
    def credentials_configured(self) -> bool:
        return bool(
            self.gsc_credentials_path and os.path.exists(self.gsc_credentials_path)
        )


def load_settings() -> Settings:
    data_state = os.environ.get("GSC_DATA_STATE", "all").lower().strip()
    if data_state not in ("all", "final"):
        raise ValueError(
            f"Invalid GSC_DATA_STATE value '{data_state}'. "
            "Accepted values are 'all' or 'final'."
        )

    try:
        mcp_port = int(os.environ.get("MCP_PORT", "3001"))
    except ValueError as exc:
        raise ValueError("MCP_PORT must be an integer") from exc

    return Settings(
        gsc_credentials_path=_expand_path(os.environ.get("GSC_CREDENTIALS_PATH")),
        skip_oauth=_env_bool("GSC_SKIP_OAUTH", default=True),
        allow_destructive=_env_bool("GSC_ALLOW_DESTRUCTIVE", default=False),
        data_state=data_state,
        primary_gsc_property=os.environ.get("PRIMARY_GSC_PROPERTY") or None,
        secondary_gsc_property=os.environ.get("SECONDARY_GSC_PROPERTY") or None,
        target_path_prefix=os.environ.get("TARGET_PATH_PREFIX") or None,
        default_days=_env_int("DEFAULT_DAYS", 90),
        min_impressions=_env_int("MIN_IMPRESSIONS", 50),
        max_rows=_env_int("MAX_ROWS", 500),
        mcp_transport=os.environ.get("MCP_TRANSPORT", "streamable-http").lower(),
        mcp_host=os.environ.get("MCP_HOST", "0.0.0.0"),
        mcp_port=mcp_port,
    )


def settings_to_public_dict(settings: Settings) -> dict:
    """Non-sensitive settings for get_config."""
    return {
        "skip_oauth": settings.skip_oauth,
        "allow_destructive": settings.allow_destructive,
        "data_state": settings.data_state,
        "primary_gsc_property": settings.primary_gsc_property,
        "secondary_gsc_property": settings.secondary_gsc_property,
        "target_path_prefix": settings.target_path_prefix,
        "default_days": settings.default_days,
        "min_impressions": settings.min_impressions,
        "max_rows": settings.max_rows,
        "mcp_transport": settings.mcp_transport,
        "mcp_host": settings.mcp_host,
        "mcp_port": settings.mcp_port,
        "credentials_configured": settings.credentials_configured,
        "gsc_credentials_path_set": bool(settings.gsc_credentials_path),
    }
