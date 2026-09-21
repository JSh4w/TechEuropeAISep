"""Seal and open a run owner's Google key. The plaintext key exists only inside `decrypt_google_key`'s caller."""

from __future__ import annotations

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from bessible.config import settings
from bessible.models import EncryptedCredentials

NONCE_BYTES = 12


class CredentialsError(Exception):
    """The run's credentials cannot be used."""


class MissingGoogleKeyError(CredentialsError):
    """The run carries no Google key."""


class InvalidCredentialsError(CredentialsError):
    """The ciphertext does not open: wrong user, unknown key id, or a changed master secret."""


def _cipher(uid: str, key_id: str) -> AESGCM:
    secret = settings.key_encryption_secret
    if secret is None:
        msg = "KEY_ENCRYPTION_SECRET is not set"
        raise InvalidCredentialsError(msg)
    if key_id != settings.key_encryption_key_id:
        msg = f"Unknown key id {key_id!r}"
        raise InvalidCredentialsError(msg)
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=uid.encode()).derive(
        secret.get_secret_value().encode()
    )
    return AESGCM(derived)


def encrypt_google_key(uid: str, api_key: str) -> EncryptedCredentials:
    """Seal `api_key` for `uid`. The uid is bound as associated data, so the ciphertext opens for that user only."""
    key_id = settings.key_encryption_key_id
    nonce = os.urandom(NONCE_BYTES)
    ciphertext = _cipher(uid, key_id).encrypt(nonce, api_key.encode(), uid.encode())
    return EncryptedCredentials(uid=uid, key_id=key_id, google_ct=base64.urlsafe_b64encode(nonce + ciphertext).decode())


def decrypt_google_key(credentials: EncryptedCredentials | None) -> str:
    """Open the run's Google key. Raises `MissingGoogleKeyError` when there is none: no server key stands in."""
    if credentials is None or not credentials.google_ct:
        msg = "This run has no Google key"
        raise MissingGoogleKeyError(msg)
    try:
        blob = base64.urlsafe_b64decode(credentials.google_ct)
        nonce, ciphertext = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
        return (
            _cipher(credentials.uid, credentials.key_id).decrypt(nonce, ciphertext, credentials.uid.encode()).decode()
        )
    except (InvalidTag, ValueError) as exc:
        msg = "The run's Google key could not be decrypted"
        raise InvalidCredentialsError(msg) from exc
