"""Bitwarden's documented unencrypted JSON and standard TOTP inputs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import struct
import uuid
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlsplit

MAX_BYTES = 25 * 1024 * 1024
MAX_ITEMS = 20_000


class MigrationError(Exception):
    """Messages must contain no source values, cookies, or server error bodies."""


@dataclass(frozen=True)
class Totp:
    secret: str = field(repr=False)
    algorithm: str = "SHA1"
    digits: int = 6
    period: int = 30

    def code(self, timestamp: int) -> str:
        key = base64.b32decode(self.secret + "=" * (-len(self.secret) % 8))
        digest = hmac.new(key, struct.pack(">Q", timestamp // self.period),
                          getattr(hashlib, self.algorithm.lower())).digest()
        offset = digest[-1] & 15
        binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff
        return str(binary % (10 ** self.digits)).zfill(self.digits)


def parse_totp(value: str) -> Totp:
    if not isinstance(value, str) or len(value) > 8192:
        raise MigrationError("Invalid TOTP input.")
    value = value.strip()
    algorithm, digits, period = "SHA1", 6, 30
    if value.lower().startswith("otpauth://"):
        uri = urlparse(value)
        if uri.scheme != "otpauth" or uri.netloc != "totp":
            raise MigrationError("Only TOTP authenticator accounts are supported.")
        query = parse_qs(uri.query, keep_blank_values=True)
        if any(len(v) != 1 for v in query.values()):
            raise MigrationError("Ambiguous TOTP parameters.")
        if set(query) - {"secret", "algorithm", "digits", "period", "issuer"}:
            raise MigrationError("Unsupported TOTP parameters.")
        value = query.get("secret", [""])[0]
        algorithm = query.get("algorithm", ["SHA1"])[0].upper()
        try:
            digits = int(query.get("digits", ["6"])[0])
            period = int(query.get("period", ["30"])[0])
        except ValueError:
            raise MigrationError("Invalid TOTP timing or digits.") from None
    secret = re.sub(r"\s", "", value).upper().rstrip("=")
    if not secret or not re.fullmatch(r"[A-Z2-7]+", secret):
        raise MigrationError("Invalid Base32 authenticator secret.")
    try:
        decoded = base64.b32decode(secret + "=" * (-len(secret) % 8))
    except Exception:
        raise MigrationError("Invalid Base32 authenticator secret.") from None
    if base64.b32encode(decoded).decode().rstrip("=") != secret:
        raise MigrationError("Noncanonical Base32 authenticator secret.")
    if algorithm not in {"SHA1", "SHA256", "SHA512"} or digits not in {6, 8} or not 1 <= period <= 300:
        raise MigrationError("Unsupported TOTP configuration.")
    return Totp(secret, algorithm, digits, period)


@dataclass(repr=False)
class Login:
    name: str
    username: str
    password: str
    totp: Totp | None = None
    source_index: int = -1
    source_id: str = ""
    source_name: str = ""
    site: str = ""

    def fields(self) -> list[dict[str, str]]:
        result = [{"key": "username", "value": self.username},
                  {"key": "password", "value": self.password}]
        if self.totp:
            result.append({"key": "totp", "value": self.totp.secret})
        return result


@dataclass
class Plan:
    source_count: int
    logins: list[Login] = field(repr=False)
    issues: list[dict]

    def report(self) -> dict:
        return {"source_items": self.source_count, "ready": len(self.logins),
                "with_password": sum(bool(x.password) for x in self.logins),
                "with_totp": sum(x.totp is not None for x in self.logins),
                "with_site": sum(bool(x.site) for x in self.logins),
                "withheld": sum(not x.get("partial", False) for x in self.issues),
                "partial": sum(bool(x.get("partial", False)) for x in self.issues),
                "issues": self.issues}


def _site_from_uris(uris) -> str:
    """Return a public hostname only; URI paths, queries and fragments may contain tokens."""
    if not isinstance(uris, list):
        return ""
    for entry in uris:
        value = entry.get("uri") if isinstance(entry, dict) else None
        if not isinstance(value, str) or len(value) > 8192 or any(ord(char) < 33 or ord(char) == 127 for char in value):
            continue
        try:
            parsed = urlsplit(value)
            host = parsed.hostname
            if parsed.scheme.lower() not in {"http", "https"} or not host or parsed.username or parsed.password:
                continue
            host = host.encode("idna").decode("ascii").lower().rstrip(".")
            if (len(host) > 253 or any(len(label) > 63 or not re.fullmatch(r"[a-z0-9-]+", label)
                                        or label.startswith("-") or label.endswith("-") for label in host.split("."))):
                continue
            return host
        except (ValueError, UnicodeError):
            continue
    return ""


def _migration_name(title: str, site: str, identifier: str) -> str:
    # The target has no source-ID or URL field, so the name carries both a readable
    # hostname and a stable marker. Keep the marker even if a long title is trimmed.
    suffix = f" [bw:{identifier}]"
    prefix = title + (f" · {site}" if site else "")
    return prefix[:240 - len(suffix)].rstrip() + suffix


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MigrationError("Duplicate JSON keys are not accepted.")
        result[key] = value
    return result


def load_plan(path: Path, password="", allow_partial=False, migration_names=False) -> Plan:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError:
        raise MigrationError("Cannot read the export file.") from None
    return loads_plan(raw, password, allow_partial, migration_names)


def loads_plan(raw, password="", allow_partial=False, migration_names=False) -> Plan:
    try:
        if len(raw) > MAX_BYTES:
            raise MigrationError("Export exceeds the 25 MiB limit.")
        data = json.loads(raw, object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError, RecursionError):
        raise MigrationError("Cannot read a valid JSON export.") from None
    if not isinstance(data, dict):
        raise MigrationError("Expected a Bitwarden JSON export.")
    if data.get("encrypted") is True:
        from .unlock import unlock_bitwarden
        decrypted = unlock_bitwarden(data, password)
        # Nested encryption envelopes are invalid, not a recursive KDF workload.
        inner = json.loads(decrypted, object_pairs_hook=_unique_object)
        if not isinstance(inner, dict) or inner.get("encrypted") is not False:
            raise MigrationError("Invalid decrypted Bitwarden export.")
        data = inner
    if data.get("encrypted") is not False:
        raise MigrationError("Expected a Bitwarden JSON export.")
    items = data.get("items")
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise MigrationError("Invalid or oversized item collection.")
    logins, issues = [], []
    for index, item in enumerate(items):
        def issue(reason):
            issues.append({"index": index, "reason": reason})
        if not isinstance(item, dict) or type(item.get("type")) is not int or item.get("type") != 1:
            issue("Unsupported item type; this prototype transfers login records only.")
            continue
        login = item.get("login")
        if not isinstance(login, dict):
            issue("Missing login data.")
            continue
        name = item.get("name")
        username = "" if login.get("username") is None else login["username"]
        password = "" if login.get("password") is None else login["password"]
        if not isinstance(name, str):
            issue("Invalid account title.")
            continue
        if migration_names:
            name = name.strip() or "Untitled Bitwarden login"
        elif not name.strip() or name != name.strip():
            issue("Missing name or surrounding whitespace; rename explicitly before migration.")
            continue
        if not isinstance(username, str) or not isinstance(password, str):
            issue("Invalid credential field type.")
            continue
        if max(len(name), len(username), len(password)) > 8192:
            issue("Credential field exceeds size limit.")
            continue
        # No silent data loss: every meaningful field outside the supported subset blocks the item.
        metadata = {"id", "type", "name", "login", "creationDate", "revisionDate",
                    "organizationId", "object", "deletedDate", "favorite", "reprompt",
                    "folderId", "collectionIds"}
        extra = [k for k, v in item.items() if k not in metadata and v not in (None, "", [], {})]
        extra += ["login." + k for k, v in login.items()
                  if k not in {"username", "password", "totp", "passwordRevisionDate"}
                  and v not in (None, "", [], {})]
        if extra:
            if not allow_partial:
                issue("Contains fields not supported by this prototype; item withheld.")
                continue
        if item.get("deletedDate"):
            issue("Deleted source item withheld.")
            continue
        try:
            totp = parse_totp(login["totp"]) if login.get("totp") else None
            if totp and (totp.algorithm, totp.digits, totp.period) != ("SHA1", 6, 30):
                raise MigrationError("Only SHA1 / 6 digits / 30 seconds has been verified with Instinct.")
        except MigrationError as exc:
            issue(str(exc))
            continue
        if not username and not password and not totp:
            issue("Empty credential record withheld.")
            continue
        identifier = ""
        if migration_names:
            try:
                identifier = str(uuid.UUID(item.get("id", "")))
            except (ValueError, TypeError, AttributeError):
                issue("Missing or invalid Bitwarden item ID; this login cannot be safely reimported.")
                continue
        site = _site_from_uris(login.get("uris")) if migration_names else ""
        destination_name = _migration_name(name, site, identifier) if migration_names else name
        if extra:
            issues.append({"index": index, "reason": "Extra source fields stay in Bitwarden.", "partial": True})
        logins.append(Login(destination_name, username, password, totp, index,
                            identifier, name, site))
    if migration_names:
        identifiers = Counter(x.source_id for x in logins)
        if any(count > 1 for count in identifiers.values()):
            raise MigrationError("Duplicate Bitwarden item IDs; no transfer attempted.")
    names = Counter(x.name.casefold() for x in logins)
    if any(count > 1 for count in names.values()):
        raise MigrationError("Duplicate source names require explicit resolution; no transfer attempted.")
    return Plan(len(items), logins, issues)
