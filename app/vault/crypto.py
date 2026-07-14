"""
Encryption engine for SecureVault 2.0.

Implements authenticated envelope encryption with AES-256-GCM:

  * A master Key-Encryption-Key (KEK) is loaded from configuration.
  * Every file is encrypted with its own random Data-Encryption-Key (DEK),
    which is then wrapped (encrypted) with the KEK.
  * AES-GCM provides confidentiality *and* integrity (an authentication tag),
    so tampering is detected on decryption. A separate SHA-256 checksum of the
    plaintext is stored for an independent integrity check.

On-disk / stored layout:
  * File blob (on disk):     file_nonce(12) || ciphertext+tag
  * Wrapped DEK (in the DB): wrap_nonce(12) || wrapped_dek+tag

This module is deliberately free of Flask model/ORM concerns; it only deals in
bytes, so it stays easy to test and reason about.
"""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app

# AES-256 key + GCM's recommended 96-bit nonce.
KEY_SIZE = 32
NONCE_SIZE = 12


class EncryptionConfigError(Exception):
    """Raised when the master key is missing or malformed."""


class EncryptionError(Exception):
    """Raised when encryption fails."""


class DecryptionError(Exception):
    """Raised when decryption or authentication fails."""


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 hex digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def decode_master_key(raw: str) -> bytes:
    """Decode a configured key string into exactly 32 raw bytes.

    Accepts (in order): 64-char hex, base64 (url-safe or standard) decoding to
    32 bytes, or a literal 32-character passphrase. Raises otherwise so a
    misconfiguration fails loudly instead of encrypting with a weak key.
    """
    if not raw:
        raise EncryptionConfigError("ENCRYPTION_KEY is not configured.")
    candidate = raw.strip()

    # 1) Hex-encoded 32 bytes.
    if len(candidate) == 64:
        try:
            return bytes.fromhex(candidate)
        except ValueError:
            pass

    # 2) Base64 (url-safe then standard), accepted only if it yields 32 bytes.
    padded = candidate + "=" * (-len(candidate) % 4)
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            decoded = decoder(padded)
        except (ValueError, base64.binascii.Error):
            continue
        if len(decoded) == KEY_SIZE:
            return decoded

    # 3) A literal 32-character key.
    if len(candidate) == KEY_SIZE:
        return candidate.encode("utf-8")

    raise EncryptionConfigError(
        "ENCRYPTION_KEY must be 32 bytes: 64-char hex, base64 of 32 bytes, "
        "or a 32-character string."
    )


def _master_key() -> bytes:
    """Load and validate the master key from the app configuration."""
    return decode_master_key(current_app.config.get("ENCRYPTION_KEY"))


def encrypt_bytes(plaintext: bytes) -> tuple[bytes, bytes, str]:
    """Encrypt plaintext with a fresh DEK wrapped by the master key.

    Returns:
        (disk_blob, wrapped_dek, checksum_hex) where ``disk_blob`` is what to
        write to disk and ``wrapped_dek`` is what to store in the database.
    """
    try:
        kek = _master_key()
        dek = os.urandom(KEY_SIZE)
        file_nonce = os.urandom(NONCE_SIZE)
        ciphertext = AESGCM(dek).encrypt(file_nonce, plaintext, None)

        wrap_nonce = os.urandom(NONCE_SIZE)
        wrapped_dek = AESGCM(kek).encrypt(wrap_nonce, dek, None)
    except EncryptionConfigError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise EncryptionError("Encryption failed.") from exc

    return file_nonce + ciphertext, wrap_nonce + wrapped_dek, sha256_hex(plaintext)


def decrypt_bytes(disk_blob: bytes, wrapped_dek: bytes) -> bytes:
    """Reverse :func:`encrypt_bytes`, returning the original plaintext.

    Raises:
        DecryptionError: if the key is wrong, data is truncated, or the GCM
            authentication tag does not verify (i.e. the data was tampered).
    """
    try:
        kek = _master_key()
        wrap_nonce, wrapped = wrapped_dek[:NONCE_SIZE], wrapped_dek[NONCE_SIZE:]
        dek = AESGCM(kek).decrypt(wrap_nonce, wrapped, None)

        file_nonce, ciphertext = disk_blob[:NONCE_SIZE], disk_blob[NONCE_SIZE:]
        return AESGCM(dek).decrypt(file_nonce, ciphertext, None)
    except InvalidTag as exc:
        raise DecryptionError("Authentication failed: the file may be corrupted "
                              "or tampered with.") from exc
    except EncryptionConfigError:
        raise
    except Exception as exc:
        raise DecryptionError("Failed to decrypt the file.") from exc
