# Password hashing and session tokens built on the standard library
import hashlib
import hmac
import secrets

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEY_LENGTH = 64


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode(), salt=salt, n=n, r=r, p=p, dklen=_KEY_LENGTH, maxmem=64 * 1024 * 1024
    )


def hash_password(password: str) -> str:
    """Return a self-describing hash: scrypt$n$r$p$salt$key (hex)."""
    salt = secrets.token_bytes(16)
    key = _scrypt(password, salt, _SCRYPT_N, _SCRYPT_R, _SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, n, r, p, salt, key = password_hash.split("$")
        if scheme != "scrypt":
            return False
        candidate = _scrypt(password, bytes.fromhex(salt), int(n), int(r), int(p))
    except ValueError:
        return False
    return hmac.compare_digest(candidate, bytes.fromhex(key))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
