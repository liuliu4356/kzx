"""简单的多用户认证：基于文件存储（users.json）、pbkdf2 密码哈希、服务端 session。"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

_USERS_FILE = Path("users.json")
_SESSION_TTL_HOURS = 24 * 7  # 7 天
_COOKIE_NAME = "sanssi_sid"


# ── 持久化 ────────────────────────────────────────────────────────────────

def _load() -> dict:
    if _USERS_FILE.exists():
        try:
            return json.loads(_USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"users": [], "sessions": {}}


def _save(data: dict) -> None:
    _USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 密码 ──────────────────────────────────────────────────────────────────

def _hash_password(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return dk.hex()


def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
    return hmac.compare_digest(_hash_password(password, salt), stored_hash)


# ── 用户 CRUD ─────────────────────────────────────────────────────────────

def user_count() -> int:
    return len(_load().get("users", []))


def get_user(username: str) -> Optional[dict]:
    for u in _load().get("users", []):
        if u.get("username") == username:
            return u
    return None


def create_user(username: str, password: str, role: str = "viewer") -> bool:
    data = _load()
    if any(u["username"] == username for u in data["users"]):
        return False
    salt = secrets.token_hex(16)
    data["users"].append({
        "username": username,
        "role": role,
        "salt": salt,
        "hash": _hash_password(password, salt),
    })
    _save(data)
    return True


def delete_user(username: str) -> bool:
    data = _load()
    before = len(data["users"])
    data["users"] = [u for u in data["users"] if u["username"] != username]
    if len(data["users"]) < before:
        # 清理该用户的所有 session
        data["sessions"] = {t: s for t, s in data.get("sessions", {}).items()
                            if s.get("username") != username}
        _save(data)
        return True
    return False


def list_users() -> list[dict]:
    return [{"username": u["username"], "role": u["role"]}
            for u in _load().get("users", [])]


# ── Session ───────────────────────────────────────────────────────────────

def login(username: str, password: str) -> Optional[str]:
    """验证密码，成功返回 session token，失败返回 None。"""
    user = get_user(username)
    if not user:
        return None
    if not _verify_password(password, user["salt"], user["hash"]):
        return None
    token = secrets.token_hex(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=_SESSION_TTL_HOURS)).isoformat()
    data = _load()
    data.setdefault("sessions", {})[token] = {
        "username": username,
        "role": user["role"],
        "expires": expires,
    }
    _save(data)
    return token


def get_session(token: str) -> Optional[dict]:
    """根据 token 返回 session 信息，已过期则删除并返回 None。"""
    if not token:
        return None
    data = _load()
    sess = data.get("sessions", {}).get(token)
    if not sess:
        return None
    try:
        exp = datetime.fromisoformat(sess["expires"])
        if datetime.now(timezone.utc) > exp:
            del data["sessions"][token]
            _save(data)
            return None
    except Exception:
        return None
    return sess


def logout(token: str) -> None:
    data = _load()
    data.get("sessions", {}).pop(token, None)
    _save(data)


def get_current_user(request) -> Optional[dict]:
    """从请求 cookie 中取出并校验 session，返回 {username, role} 或 None。"""
    token = request.cookies.get(_COOKIE_NAME, "")
    return get_session(token)


COOKIE_NAME = _COOKIE_NAME
