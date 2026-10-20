"""Streamlit Community Cloud settings; secrets stay on the hosting service."""
from __future__ import annotations

import os
from collections.abc import Mapping

ALLOWED_SETTINGS = frozenset({
    "PUBLIC_ADMIN_USERNAME", "PUBLIC_ADMIN_PASSWORD", "DATABASE_URL", "SECRET_KEY",
    "DEMO_MODE", "SEED_DEMO_DATA", "KNOWLEDGE_DB_PATH", "WATER_3D_TILESET_URL",
    "WATER_AI_BASE_URL", "WATER_AI_MODEL", "WATER_AI_API_KEY",
})


def apply_cloud_settings(settings: Mapping | None = None) -> None:
    if settings is None:
        import streamlit as st
        from streamlit.errors import StreamlitSecretNotFoundError
        try:
            settings = dict(st.secrets)
        except (FileNotFoundError, StreamlitSecretNotFoundError):
            settings = {}
    settings = settings.get("platform", settings)
    if not isinstance(settings, Mapping):
        raise ValueError("The platform secrets section must be a table")
    for name in ALLOWED_SETTINGS:
        value = settings.get(name)
        if value is None:
            continue
        if not isinstance(value, (str, bool, int, float)):
            raise ValueError(f"Invalid configuration type for {name}")
        os.environ.setdefault(name, str(value).lower() if isinstance(value, bool) else str(value))
    # This entry point must not expose local development accounts, even if
    # an environment or .env file mistakenly requests development mode.
    os.environ["APP_ENV"] = "public"

