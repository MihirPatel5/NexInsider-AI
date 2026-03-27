"""
security/encryption.py — Data at rest encryption.
Uses Fernet symmetric encryption for sensitive API keys and PII.
"""
from cryptography.fernet import Fernet
from data.config import settings
import base64

def get_encryptor():
    # In production, this key should come from AWS KMS or HashiCorp Vault
    key = settings.encryption_key.encode()
    return Fernet(key)

def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    if not value: return ""
    f = get_encryptor()
    return f.encrypt(value.encode()).decode()

def decrypt_value(token: str) -> str:
    """Decrypt a token back to string."""
    if not token: return ""
    f = get_encryptor()
    return f.decrypt(token.encode()).decode()
