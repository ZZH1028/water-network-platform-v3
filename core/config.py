from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / '.env', override=False)

APP_NAME = os.getenv("APP_NAME", "水网工程水力调控智能平台")
APP_VERSION = os.getenv("APP_VERSION", "V5.0 实景三维 · 水知助手")
APP_ENV = os.getenv("APP_ENV", "development")
PUBLIC_DEPLOYMENT = APP_ENV.lower() in {"public", "production"}
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
SEED_DEMO_DATA = os.getenv("SEED_DEMO_DATA", "true").lower() == "true"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(BASE_DIR / 'database' / 'platform_dev.db').as_posix()}",
)
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-before-production")

SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8501"))
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
EXPORT_DIR = BASE_DIR / "storage" / "exports"
BACKUP_DIR = BASE_DIR / "backups"

for directory in [UPLOAD_DIR, EXPORT_DIR, BACKUP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
