# Password hashing and session tokens built on the standard library
import hashlib
import hmac
import secrets
import string

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEY_LENGTH = 64
MIN_PASSWORD_LENGTH = 12
# Letters and digits without look-alikes, for passwords read out to patients and doctors
_PASSWORD_ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")


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


# Verified against for unknown emails, so both cases take the same time
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(session_token: str) -> str:
    """Form token bound to the session; another site can neither read nor compute it."""
    return hmac.new(session_token.encode(), b"csrf", hashlib.sha256).hexdigest()


def generate_password(length: int = 14) -> str:
    """Random initial password for a patient or doctor account."""
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))
