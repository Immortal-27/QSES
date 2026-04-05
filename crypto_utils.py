"""
Cryptographic utilities for Quantum-Simulated Email Security.

Uses AES-256-GCM (Galois/Counter Mode) for authenticated encryption
with an additional HMAC-SHA256 integrity layer over the ciphertext.

GCM provides both confidentiality and integrity, while the HMAC adds
an independent verification layer — if either check fails, the message
is rejected as tampered.

Key derivation uses HKDF (HMAC-based Key Derivation Function) to stretch
the BB84-derived key material into separate AES and HMAC keys.
"""

import hmac
import hashlib
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def derive_keys(key_hex: str) -> tuple[bytes, bytes]:
    """
    Derive separate AES-256 and HMAC-SHA256 keys from the BB84 sifted key.

    Uses HKDF with distinct `info` labels to produce two independent
    32-byte keys from the same input material:
      - AES key  (info=b"qses-aes-key-v2")
      - HMAC key (info=b"qses-hmac-key-v2")

    Args:
        key_hex: Hexadecimal string from the BB84 key exchange

    Returns:
        (aes_key, hmac_key) — two 32-byte keys
    """
    key_material = bytes.fromhex(key_hex) if key_hex else os.urandom(32)

    aes_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"qses-aes-key-v2",
    ).derive(key_material)

    hmac_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"qses-hmac-key-v2",
    ).derive(key_material)

    return aes_key, hmac_key


def _compute_hmac(hmac_key: bytes, nonce: bytes, ciphertext: bytes) -> str:
    """
    Compute HMAC-SHA256 over nonce || ciphertext.

    Binding the nonce into the HMAC prevents an attacker from swapping
    nonces between messages without detection.

    Returns:
        Hex-encoded HMAC tag
    """
    h = hmac.new(hmac_key, digestmod=hashlib.sha256)
    h.update(nonce)
    h.update(ciphertext)
    return h.hexdigest()


def encrypt_message(plaintext: str, key_hex: str) -> dict:
    """
    Encrypt a message using AES-256-GCM + HMAC-SHA256.

    Security layers:
    - AES-256-GCM: Confidentiality + integrity (via GCM auth tag)
    - HMAC-SHA256:  Independent integrity verification over (nonce || ciphertext)

    Args:
        plaintext: The email/message content to encrypt
        key_hex: Hex string key from BB84 exchange

    Returns:
        dict with hex-encoded nonce, ciphertext, HMAC tag, and metadata
    """
    aes_key, hmac_key = derive_keys(key_hex)
    aesgcm = AESGCM(aes_key)

    # 96-bit nonce (recommended for GCM)
    nonce = os.urandom(12)

    # Encrypt with associated data for additional authentication
    aad = b"QSES-v1-quantum-simulated"
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)

    # Compute HMAC-SHA256 over nonce || ciphertext
    hmac_tag = _compute_hmac(hmac_key, nonce, ciphertext)

    return {
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex(),
        "hmac": hmac_tag,
        "algorithm": "AES-256-GCM",
        "integrity": "HMAC-SHA256",
        "key_derivation": "HKDF-SHA256",
        "key_source": "BB84-Simulated-QKD",
        "aad": aad.decode("ascii"),
    }


def decrypt_message(nonce_hex: str, ciphertext_hex: str, key_hex: str, hmac_tag: str = "") -> str:
    """
    Verify HMAC and decrypt an AES-256-GCM encrypted message.

    Verification order:
    1. HMAC-SHA256 check (fast rejection of tampered messages)
    2. AES-GCM decryption (secondary integrity via GCM auth tag)

    Args:
        nonce_hex: Hex-encoded nonce
        ciphertext_hex: Hex-encoded ciphertext
        key_hex: Hex string key from BB84 exchange
        hmac_tag: Hex-encoded HMAC-SHA256 tag (optional for backward compat)

    Returns:
        Decrypted plaintext string

    Raises:
        ValueError: If HMAC verification fails
        cryptography.exceptions.InvalidTag: If GCM ciphertext was tampered with
    """
    aes_key, hmac_key = derive_keys(key_hex)

    nonce = bytes.fromhex(nonce_hex)
    ciphertext = bytes.fromhex(ciphertext_hex)

    # Step 1: Verify HMAC (Mandatory)
    if not hmac_tag:
        raise ValueError("Missing HMAC tag — ciphertext integrity cannot be verified.")
        
    expected_hmac = _compute_hmac(hmac_key, nonce, ciphertext)
    if not hmac.compare_digest(hmac_tag, expected_hmac):
        raise ValueError(
            "HMAC verification failed — the ciphertext has been tampered with "
            "or the wrong key was used."
        )

    # Step 2: AES-GCM decryption (also verifies integrity via auth tag)
    aesgcm = AESGCM(aes_key)
    aad = b"QSES-v1-quantum-simulated"
    plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
    return plaintext.decode("utf-8")
