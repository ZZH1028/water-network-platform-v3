from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import os
import re

from sqlalchemy import select

from database.engine import session_scope
from database.models import User
from core.config import PUBLIC_DEPLOYMENT

ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except Exception:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    if PUBLIC_DEPLOYMENT and (len(password) < 12 or password in {"admin123", "demo123"}):
        return False, "公网账号密码至少12位，并包含字母和数字"
    if len(password) < 8:
        return False, "密码长度至少为8位"
    if not re.search(r"[a-zA-Z]", password):
        return False, "密码必须包含至少一个字母"
    if not re.search(r"\d", password):
        return False, "密码必须包含至少一个数字"
    return True, ""


def authenticate(username: str, password: str) -> dict | None:
    if PUBLIC_DEPLOYMENT and password in {"admin123", "demo123"}:
        return None
    with session_scope() as session:
        user = session.scalar(select(User).where(User.username == username, User.enabled.is_(True)))
        if not user or not verify_password(password, user.password_hash):
            return None
        user.last_login_at = datetime.now()
        return {"username": user.username, "role": user.role, "user_id": user.id}


def create_or_update_user(username: str, password: str, role: str, enabled: bool = True) -> tuple[bool, str]:
    valid, msg = validate_password_strength(password)
    if not valid:
        return False, msg
    with session_scope() as session:
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(username=username, password_hash=hash_password(password), role=role, enabled=enabled)
            session.add(user)
            return True, f"用户 {username} 创建成功"
        else:
            user.password_hash = hash_password(password)
            user.role = role
            user.enabled = enabled
            return True, f"用户 {username} 更新成功"


def list_users() -> list[dict]:
    with session_scope() as session:
        rows = session.scalars(select(User).order_by(User.id)).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "enabled": u.enabled,
            "last_login_at": u.last_login_at,
            "created_at": u.created_at,
            "updated_at": u.updated_at,
        }
        for u in rows
    ]


def set_user_enabled(username: str, enabled: bool) -> bool:
    with session_scope() as session:
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            return False
        user.enabled = enabled
        return True


def delete_user(username: str) -> bool:
    with session_scope() as session:
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            return False
        user.enabled = False
        return True


def update_user_role(username: str, role: str) -> bool:
    with session_scope() as session:
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            return False
        user.role = role
        return True


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    valid, msg = validate_password_strength(new_password)
    if not valid:
        return False, msg
    with session_scope() as session:
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            return False, "用户不存在"
        if not verify_password(old_password, user.password_hash):
            return False, "旧密码不正确"
        user.password_hash = hash_password(new_password)
        return True, "密码修改成功"
