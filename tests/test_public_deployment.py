from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.cloud import apply_cloud_settings
from database import init_db
from database.engine import Base
from services import auth_service as auth


@pytest.fixture
def public_db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'public.db'}")
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def session_scope():
        with factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    monkeypatch.setattr(init_db, "engine", engine)
    monkeypatch.setattr(init_db, "session_scope", session_scope)
    monkeypatch.setattr(auth, "session_scope", session_scope)
    monkeypatch.setattr(init_db, "PUBLIC_DEPLOYMENT", True)
    monkeypatch.setattr(auth, "PUBLIC_DEPLOYMENT", True)
    monkeypatch.delenv("PUBLIC_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("PUBLIC_ADMIN_USERNAME", raising=False)
    yield
    engine.dispose()


def test_public_startup_does_not_create_default_or_takeover_accounts(public_db):
    init_db.initialize_database()
    assert auth.list_users() == []
    assert auth.authenticate("admin", "admin123") is None


def test_configured_owner_can_login_and_restart_preserves_changed_password(public_db, monkeypatch):
    monkeypatch.setenv("PUBLIC_ADMIN_USERNAME", "owner")
    monkeypatch.setenv("PUBLIC_ADMIN_PASSWORD", "ConfiguredPass123!")
    init_db.initialize_database()
    assert auth.authenticate("owner", "ConfiguredPass123!")["role"] == "管理员"
    ok, _ = auth.change_password("owner", "ConfiguredPass123!", "ChangedPassword567!")
    assert ok
    init_db.initialize_database()
    assert auth.authenticate("owner", "ConfiguredPass123!") is None
    assert auth.authenticate("owner", "ChangedPassword567!")


@pytest.mark.parametrize("password", ["admin123", "demo123", "Short123", "abcdefghijklmnop", "1234567890123"])
def test_public_bootstrap_rejects_unsafe_password_without_echo(public_db, monkeypatch, password):
    monkeypatch.setenv("PUBLIC_ADMIN_PASSWORD", password)
    with pytest.raises(ValueError) as error:
        init_db.initialize_database()
    assert password not in str(error.value)
    assert auth.list_users() == []


def test_legacy_demo_accounts_cannot_login_after_switching_to_public(public_db, monkeypatch):
    monkeypatch.setattr(init_db, "PUBLIC_DEPLOYMENT", False)
    init_db.initialize_database()
    assert len(auth.list_users()) == 4
    assert auth.authenticate("admin", "admin123") is None
    assert auth.authenticate("researcher", "demo123") is None
    monkeypatch.setattr(init_db, "PUBLIC_DEPLOYMENT", True)
    monkeypatch.setenv("PUBLIC_ADMIN_PASSWORD", "ReplacementPass123!")
    init_db.initialize_database()
    assert auth.authenticate("admin", "ReplacementPass123!")


def test_public_user_management_cannot_restore_known_demo_password(public_db):
    init_db.initialize_database()
    ok, _ = auth.create_or_update_user("owner", "admin123", "管理员")
    assert not ok and auth.list_users() == []


def test_cloud_secrets_are_applied_before_config_and_force_public_mode(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("PUBLIC_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("WATER_AI_MODEL", raising=False)
    monkeypatch.delenv("IGNORED_SETTING", raising=False)
    apply_cloud_settings({"platform": {"PUBLIC_ADMIN_USERNAME": "owner", "WATER_AI_MODEL": "example", "IGNORED_SETTING": "ignored"}})
    import os
    assert os.environ["APP_ENV"] == "public"
    assert os.environ["PUBLIC_ADMIN_USERNAME"] == "owner"
    assert os.environ["WATER_AI_MODEL"] == "example"
    assert "IGNORED_SETTING" not in os.environ


def test_cloud_settings_preserve_existing_environment_bindings(monkeypatch):
    monkeypatch.setenv("WATER_AI_MODEL", "bound-model")
    monkeypatch.setenv("APP_ENV", "development")
    apply_cloud_settings({"platform": {"WATER_AI_MODEL": "file-model"}})
    import os
    assert os.environ["WATER_AI_MODEL"] == "bound-model"


def test_invalid_secret_table_is_rejected_without_echo():
    with pytest.raises(ValueError, match="table"):
        apply_cloud_settings({"platform": "invalid"})
