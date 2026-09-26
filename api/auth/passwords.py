from __future__ import annotations

from passlib.context import CryptContext

PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
BCRYPT_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return PASSWORD_CONTEXT.hash(password[:BCRYPT_MAX_PASSWORD_BYTES])


def verify_password(password: str, hashed_password: str) -> bool:
    return PASSWORD_CONTEXT.verify(password[:BCRYPT_MAX_PASSWORD_BYTES], hashed_password)
