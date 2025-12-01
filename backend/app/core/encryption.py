"""
Token encryption for secure storage of OAuth tokens.
"""
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64


def _get_encryption_key() -> bytes:
    """Derive a Fernet key from SECRET_KEY."""
    
    secret = os.getenv("SECRET_KEY", "").encode()
    if not secret:
        raise ValueError("SECRET_KEY not set")
    
    # Use PBKDF2 to derive a proper key
    salt = b"habexa_token_salt_v1"  # Static salt is OK here since SECRET_KEY is unique
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret))
    return key


def encrypt_token(token: str) -> str:
    """Encrypt a token for database storage."""
    
    if not token:
        return ""
    
    f = Fernet(_get_encryption_key())
    encrypted = f.encrypt(token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token from database storage."""
    
    if not encrypted_token:
        return ""
    
    f = Fernet(_get_encryption_key())
    decrypted = f.decrypt(encrypted_token.encode())
    return decrypted.decode()

