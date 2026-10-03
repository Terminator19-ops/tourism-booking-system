import hashlib
import hmac
import os
import secrets
from typing import Any, Dict, Optional

SESSION_STORE: Dict[str, Dict[str, Any]] = {}
JWT_SECRET = os.getenv("JWT_SECRET", "tourism-booking-platform-secret")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200000,
    )
    return f"pbkdf2_sha256$200000${salt}${derived.hex()}"


def verify_password(plain_password: str, stored_hash: Optional[str]) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations, salt, expected_hash = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    )
    return hmac.compare_digest(derived.hex(), expected_hash)


def normalize_role(role: Optional[str]) -> str:
    return (role or "").strip().upper()


def create_session(user: Dict[str, Any]) -> str:
    token = secrets.token_urlsafe(32)
    SESSION_STORE[token] = user
    return token


def get_session_user(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    return SESSION_STORE.get(token)


def invalidate_session(token: Optional[str]) -> None:
    if token:
        SESSION_STORE.pop(token, None)


def serialize_user(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": row.get("USER_ID") or row.get("user_id"),
        "first_name": row.get("FIRST_NAME") or row.get("first_name"),
        "last_name": row.get("LAST_NAME") or row.get("last_name"),
        "email": row.get("EMAIL") or row.get("email"),
        "phone": row.get("PHONE") or row.get("phone"),
        "role": row.get("ROLE") or row.get("role"),
        "status": row.get("STATUS") or row.get("status"),
    }
