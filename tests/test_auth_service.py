import os, sys
from pathlib import Path
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(__file__).parent / 'test_auth.db').as_posix()}"
os.environ["SEED_DEMO_DATA"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(str(Path(__file__).resolve().parents[1]))

from database.init_db import initialize_database
from services.auth_service import (
    hash_password, verify_password, validate_password_strength,
    authenticate, create_or_update_user, list_users,
    set_user_enabled, delete_user, update_user_role, change_password,
)


def setup_module():
    initialize_database(seed_demo=False)


class TestPasswordStrength:
    def test_too_short(self):
        ok, msg = validate_password_strength("short")
        assert not ok
        assert "8位" in msg

    def test_no_letter(self):
        ok, msg = validate_password_strength("12345678")
        assert not ok
        assert "字母" in msg

    def test_no_digit(self):
        ok, msg = validate_password_strength("abcdefgh")
        assert not ok
        assert "数字" in msg

    def test_valid(self):
        ok, msg = validate_password_strength("pass1234")
        assert ok


class TestAuthenticate:
    def test_login_success(self):
        result = authenticate("admin", "admin123")
        assert result is not None
        assert result["username"] == "admin"

    def test_wrong_password(self):
        result = authenticate("admin", "wrong")
        assert result is None

    def test_disabled_user(self):
        create_or_update_user("test_disabled", "pass1234", "查看用户")
        set_user_enabled("test_disabled", False)
        result = authenticate("test_disabled", "pass1234")
        assert result is None


class TestUserManagement:
    def test_create_user_weak_password(self):
        ok, msg = create_or_update_user("test_weak", "short", "查看用户")
        assert not ok

    def test_create_user_valid(self):
        ok, msg = create_or_update_user("test_create", "pass1234", "科研人员")
        assert ok
        users = list_users()
        usernames = [u["username"] for u in users]
        assert "test_create" in usernames

    def test_list_users(self):
        users = list_users()
        assert len(users) >= 4  # admin, researcher, dispatcher, viewer

    def test_set_enabled(self):
        create_or_update_user("test_toggle", "pass1234", "查看用户")
        ok = set_user_enabled("test_toggle", False)
        assert ok
        result = authenticate("test_toggle", "pass1234")
        assert result is None
        ok = set_user_enabled("test_toggle", True)
        assert ok

    def test_update_role(self):
        create_or_update_user("test_role", "pass1234", "查看用户")
        ok = update_user_role("test_role", "科研人员")
        assert ok
        users = list_users()
        u = [u for u in users if u["username"] == "test_role"][0]
        assert u["role"] == "科研人员"

    def test_delete_user(self):
        create_or_update_user("test_del", "pass1234", "查看用户")
        ok = delete_user("test_del")
        assert ok
        users = list_users()
        u = [u for u in users if u["username"] == "test_del"][0]
        assert u["enabled"] is False


class TestChangePassword:
    def test_wrong_old_password(self):
        create_or_update_user("test_pwd", "pass1234", "查看用户")
        ok, msg = change_password("test_pwd", "wrong", "newpass1")
        assert not ok

    def test_weak_new_password(self):
        ok, msg = change_password("test_pwd", "pass1234", "short")
        assert not ok

    def test_successful_change(self):
        ok, msg = change_password("test_pwd", "pass1234", "newpass1")
        assert ok
        result = authenticate("test_pwd", "pass1234")
        assert result is None
        result = authenticate("test_pwd", "newpass1")
        assert result is not None
