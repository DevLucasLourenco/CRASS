import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from datetime import timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DbSession

from .db import get_db
from .models import Session, User, now


COOKIE_NAME = "crass_session"
SESSION_DAYS = 7


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("A senha deve ter pelo menos 12 caracteres.")
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(key).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt_text, key_text = stored.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(key_text)
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_session(db: DbSession, user: User) -> str:
    token = secrets.token_urlsafe(48)
    db.add(Session(id=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                   expires_at=now() + timedelta(days=SESSION_DAYS)))
    db.commit()
    return token


def session_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_for(token: str) -> str:
    secret = os.getenv("SESSION_SECRET", "")
    if not secret:
        raise RuntimeError("SESSION_SECRET não configurado.")
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def current_user(request: Request, db: DbSession = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Entre na sua conta.")
    session = db.get(Session, session_hash(token))
    if not session or session.expires_at <= now():
        raise HTTPException(401, "Sessão expirada.")
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, "Conta indisponível.")
    if user.must_change_password and request.url.path not in (
        "/auth/me", "/auth/password", "/auth/logout"
    ):
        raise HTTPException(403, "Troque a senha temporária antes de continuar.")
    return user


def require(*roles: str):
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Sem permissão para esta ação.")
        return user
    return check


def new_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode().rstrip("=")


def totp_at(secret: str, timestamp: int) -> str:
    raw = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
    counter = struct.pack(">Q", timestamp // 30)
    digest = hmac.new(raw, counter, hashlib.sha1).digest()
    offset = digest[-1] & 15
    number = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000
    return f"{number:06d}"


def verify_totp(secret: str, code: str) -> bool:
    if not code or not code.isdigit() or len(code) != 6:
        return False
    current = int(time.time())
    return any(hmac.compare_digest(totp_at(secret, current + shift), code)
               for shift in (-30, 0, 30))


def recovery_hash(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def generate_recovery_codes() -> tuple[list[str], list[str]]:
    codes = [secrets.token_hex(5).upper() for _ in range(10)]
    return codes, [recovery_hash(code) for code in codes]
