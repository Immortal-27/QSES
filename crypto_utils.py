"""
Cryptographic utilities for Quantum-Simulated Email Security.

Uses AES-256-GCM (Galois/Counter Mode) for authenticated encryption.
GCM provides both confidentiality and integrity, preventing tampering attacks
that CBC mode is vulnerable to (e.g., padding oracle attacks).

Key derivation uses HKDF (HMAC-based Key Derivation Function) to stretch
the BB84-derived key material into a proper AES-256 key.
"""

import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def derive_aes_key(key_hex: str) -> bytes:
    """
    Derive a 256-bit AES key from the BB84 sifted key using HKDF.

    HKDF ensures the key has uniform randomness distribution even if
    the input material has slight biases from the simulation.

    Args:
        key_hex: Hexadecimal string from the BB84 key exchange

    Returns:
        32-byte AES-256 key
    """
    key_material = bytes.fromhex(key_hex) if key_hex else os.urandom(32)

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits
        salt=None,
        info=b"qses-email-encryption-v1",
    )
    return hkdf.derive(key_material)


def encrypt_message(plaintext: str, key_hex: str) -> dict:
    """
    Encrypt a message using AES-256-GCM.

    AES-GCM provides:
    - Confidentiality: Message content is hidden
    - Integrity: Any tampering is detected
    - Authentication: Verifies the message came from someone with the key

    Args:
        plaintext: The email/message content to encrypt
        key_hex: Hex string key from BB84 exchange

    Returns:
        dict with base64-encoded nonce, ciphertext, and metadata
    """
    aes_key = derive_aes_key(key_hex)
    aesgcm = AESGCM(aes_key)

    # 96-bit nonce (recommended for GCM)
    nonce = os.urandom(12)

    # Encrypt with associated data for additional authentication
    aad = b"QSES-v1-quantum-simulated"
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)

    return {
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        "algorithm": "AES-256-GCM",
        "key_derivation": "HKDF-SHA256",
        "key_source": "BB84-Simulated-QKD",
        "aad": aad.decode("ascii"),
    }


def decrypt_message(nonce_b64: str, ciphertext_b64: str, key_hex: str) -> str:
    """
    Decrypt an AES-256-GCM encrypted message.

    If the ciphertext has been tampered with, GCM will raise an
    InvalidTag exception — this is the integrity guarantee.

    Args:
        nonce_b64: Base64-encoded nonce
        ciphertext_b64: Base64-encoded ciphertext
        key_hex: Hex string key from BB84 exchange

    Returns:
        Decrypted plaintext string

    Raises:
        cryptography.exceptions.InvalidTag: If ciphertext was tampered with
    """
    aes_key = derive_aes_key(key_hex)
    aesgcm = AESGCM(aes_key)

    nonce = base64.b64decode(nonce_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    aad = b"QSES-v1-quantum-simulated"

    plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
    return plaintext.decode("utf-8")
