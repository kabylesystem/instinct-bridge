"""Local decryption using standard cryptographic libraries; never writes plaintext.

Bitwarden format: sdk-internal/crates/bitwarden-exporters/src/encrypted_json.rs
and bitwarden-crypto/src/keys/{pin_key,kdf,utils}.rs, reviewed 2026-09-24.
"""
import base64
import hashlib
import hmac

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

from .source import MigrationError


def bounded_int(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise MigrationError("Invalid or excessive cryptographic parameters.")
    return value


def aes_cbc_decrypt(ciphertext, key, iv):
    if len(iv) != 16 or not ciphertext or len(ciphertext) % 16:
        raise ValueError("Invalid block lengths")
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpad = padding.PKCS7(128).unpadder()
    return unpad.update(padded) + unpad.finalize()


def unlock_bitwarden(document, password):
    if document.get("passwordProtected") is not True:
        raise MigrationError("Use a password-protected Bitwarden export; account-restricted backups are not portable.")
    if not isinstance(password, str) or not password or len(password) > 4096:
        raise MigrationError("Enter the export password.")
    salt = document.get("salt")
    if not isinstance(salt, str) or not 1 <= len(salt) <= 256:
        raise MigrationError("Invalid encrypted export salt.")
    kind = document.get("kdfType")
    if type(kind) is not int or kind not in (0, 1):
        raise MigrationError("Unsupported Bitwarden key derivation.")
    if kind == 0:
        iterations = bounded_int(document.get("kdfIterations"), 1, 2_000_000)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations, 32)
    else:
        from argon2.low_level import Type, hash_secret_raw
        iterations = bounded_int(document.get("kdfIterations"), 1, 10)
        memory = bounded_int(document.get("kdfMemory"), 8, 256)
        parallelism = bounded_int(document.get("kdfParallelism"), 1, 16)
        key = hash_secret_raw(password.encode(), hashlib.sha256(salt.encode()).digest(),
                              iterations, memory * 1024, parallelism, 32, Type.ID, version=19)
    enc = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b"enc").derive(key)
    mac = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b"mac").derive(key)

    def decrypt(value):
        if not isinstance(value, str) or not value.startswith("2."):
            raise ValueError("Unsupported cipher")
        parts = value[2:].split("|")
        if len(parts) != 3:
            raise ValueError("Malformed cipher")
        iv, ciphertext, signature = [base64.b64decode(x, validate=True) for x in parts]
        if len(signature) != 32 or not hmac.compare_digest(signature, hmac.digest(mac, iv + ciphertext, "sha256")):
            raise ValueError("Integrity check failed")
        return aes_cbc_decrypt(ciphertext, enc, iv)
    try:
        decrypt(document["encKeyValidation_DO_NOT_EDIT"])
        return decrypt(document["data"])
    except Exception:
        raise MigrationError("Wrong export password or damaged encrypted export.") from None
