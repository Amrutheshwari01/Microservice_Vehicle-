import os
import base64
import hashlib
from typing import Tuple

from app.config import settings

def ensure_storage_dir():
    os.makedirs(settings.ENCRYPTED_STORE_PATH, exist_ok=True)

def store_encrypted_document(file_bytes: bytes, filename: str) -> str:
    """
    Simulates AES-256 encrypted-at-rest file storage for RC documents and condition photos (RTO-N06).
    In production this binds to KMS/HSM and encrypted S3/GCS.
    """
    ensure_storage_dir()
    # Simple XOR-hash simulation of envelope encryption
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    encrypted_bytes = bytes([b ^ key[i % len(key)] for i, b in enumerate(file_bytes)])
    
    file_id = hashlib.sha256(file_bytes).hexdigest()[:16]
    sanitized_name = f"enc_{file_id}_{filename}"
    file_path = os.path.join(settings.ENCRYPTED_STORE_PATH, sanitized_name)
    
    with open(file_path, "wb") as f:
        f.write(encrypted_bytes)
        
    return f"enc://{sanitized_name}"

def read_encrypted_document(file_ref: str) -> bytes:
    ensure_storage_dir()
    sanitized_name = file_ref.replace("enc://", "")
    file_path = os.path.join(settings.ENCRYPTED_STORE_PATH, sanitized_name)
    if not os.path.exists(file_path):
        return b""
    with open(file_path, "rb") as f:
        encrypted_bytes = f.read()
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    decrypted_bytes = bytes([b ^ key[i % len(key)] for i, b in enumerate(encrypted_bytes)])
    return decrypted_bytes

