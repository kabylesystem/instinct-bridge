"""Read already-captured Authy backups; capture from an iPhone is a separate step.

Format reference: valentin-dirken/authy-export at 074d46069f827264b58c0ee0737bdb9fe0d07da5.
No network calls, no device registration, no plaintext output files.
"""
import base64
import hashlib
import json
from dataclasses import dataclass, field, replace

from .source import Login, MigrationError, Totp, _unique_object, parse_totp
from .unlock import aes_cbc_decrypt, bounded_int


@dataclass(repr=False)
class AuthyAccount:
    id: str
    name: str
    issuer: str
    totp: Totp = field(repr=False)


def load_authy(raw, password=""):
    if not isinstance(raw, (bytes, str)) or len(raw) > 10 * 1024 * 1024:
        raise MigrationError("Invalid or oversized Authy export.")
    try:
        data = json.loads(raw, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, RecursionError):
        raise MigrationError("Cannot read the Authy export.") from None
    tokens = data.get("authenticator_tokens") if isinstance(data, dict) else data
    if not isinstance(tokens, list) or not 1 <= len(tokens) <= 1000:
        raise MigrationError("Expected an Authy token export, not a six-digit code.")
    if not isinstance(password, str) or len(password) > 4096:
        raise MigrationError("Invalid backup password.")
    accounts, seen, work = [], set(), 0
    for index, token in enumerate(tokens):
        if not isinstance(token, dict):
            raise MigrationError("Invalid Authy account.")
        identifier = str(token.get("unique_id") or token.get("id") or index)
        if identifier in seen:
            raise MigrationError("Duplicate Authy account identifiers; export needs review.")
        seen.add(identifier)
        name, issuer = token.get("name", ""), token.get("issuer") or ""
        if not isinstance(name, str) or not isinstance(issuer, str) or not name or max(len(name), len(issuer), len(identifier)) > 1024:
            raise MigrationError("Invalid Authy account identity.")
        if "decrypted_seed" in token:
            seed = token["decrypted_seed"]
        else:
            if not password:
                raise MigrationError("Enter your Authy backup password to unlock the captured tokens.")
            rounds = bounded_int(token.get("key_derivation_iterations", 100000), 1, 1_000_000)
            work += rounds
            if work > 30_000_000:
                raise MigrationError("Authy decryption exceeds this batch's work limit; split the encrypted export.")
            salt = token.get("salt")
            if not isinstance(salt, str) or not 1 <= len(salt) <= 256:
                raise MigrationError("Invalid Authy salt.")
            try:
                encrypted = base64.b64decode(token["encrypted_seed"], validate=True)
                if len(encrypted) > 8192:
                    raise ValueError()
                iv = bytes.fromhex(token.get("unique_iv") or "00" * 16)
                key = hashlib.pbkdf2_hmac("sha1", password.encode(), salt.encode(), rounds, 32)
                seed = aes_cbc_decrypt(encrypted, key, iv).decode("utf-8")
            except Exception:
                raise MigrationError("Wrong Authy backup password or damaged token data.") from None
        config = parse_totp(seed)
        digits = token.get("digits", 6)
        if isinstance(digits, str) and digits in ("6", "8"):
            digits = int(digits)
        algorithm = token.get("algorithm", "SHA1")
        if (type(digits) is not int or digits != 6 or not isinstance(algorithm, str)
                or algorithm.upper() != "SHA1" or token.get("period", 30) != 30
                or (config.algorithm, config.digits, config.period) != ("SHA1", 6, 30)):
            raise MigrationError("This Authy account is not a verified SHA1 / 6 digit / 30 second TOTP.")
        accounts.append(AuthyAccount(identifier, name, issuer, config))
    return accounts


def match_candidates(account, logins):
    """Suggestions only: ambiguous labels never silently bind a seed to a login."""
    service_matches = [i for i, login in enumerate(logins)
                       if (login.source_name or login.name).casefold() in {account.name.casefold(), account.issuer.casefold()}]
    return service_matches or [i for i, login in enumerate(logins)
                              if login.username and login.username.casefold() == account.name.casefold()]


def attach_authy(logins: list[Login], accounts: list[AuthyAccount], mapping: dict):
    by_id = {x.id: x for x in accounts}
    if not isinstance(mapping, dict) or set(mapping) - by_id.keys():
        raise MigrationError("Invalid Authy mapping.")
    result = list(logins)
    targets = set()
    for identifier, index in mapping.items():
        if type(index) is not int or not 0 <= index < len(result) or index in targets:
            raise MigrationError("Each Authy key must be paired with a distinct valid account.")
        targets.add(index)
        account, login = by_id[identifier], result[index]
        if login.totp is not None and login.totp != account.totp:
            raise MigrationError("Bitwarden and Authy have different keys for a selected account; resolve the conflict first.")
        result[index] = replace(login, totp=account.totp)
    return result
