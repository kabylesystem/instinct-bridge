"""Observed Instinct web operations, executed in an isolated browser session.

Contract observed in Instinct's own web client on 2026-09-24. This is an
unofficial integration and may break when the service changes.
"""

from __future__ import annotations

import shutil
import time
import hashlib
import os
import re
from dataclasses import replace
from pathlib import Path
from contextlib import contextmanager

from .source import Login, MigrationError, parse_totp

URL = "https://api.instinct.com/-/api/graphql"
VAULT_QUERY = """query useVaultQuery {
  vaultEntries { kind name isAgentEntry fields { key populated } }
  vaultKinds { kind subfieldKeys }
}"""
UPSERT = """mutation useVaultUpsertMutation($input: VaultUpsertInput!) {
  upsertVaultEntry(input: $input) { kind name isAgentEntry fields { key populated } }
}"""
REVEAL = """mutation useVaultRevealMutation($kind: String!, $name: String!, $key: String!) {
  revealVaultSubfieldValue(kind: $kind, name: $name, key: $key)
}"""
DELETE = """mutation useVaultDeleteMutation($kind: String!, $name: String!) {
  deleteVaultEntry(kind: $kind, name: $name)
}"""


@contextmanager
def brave_session():
    """Opt-in at CLI. Read only Instinct's cookie, keep it in memory, never save state."""
    import browser_cookie3
    from playwright.sync_api import sync_playwright

    try:
        cookies = [{"name": x.name, "value": x.value, "domain": x.domain,
                    "path": x.path, "secure": bool(x.secure), "httpOnly": True,
                    "sameSite": "Lax"}
                   for x in browser_cookie3.brave(domain_name="api.instinct.com")
                   if x.domain == "api.instinct.com" and x.name == "__Host-instinct_session"]
    except Exception:
        raise MigrationError("Cannot load the local Instinct session from Brave.") from None
    if not cookies:
        raise MigrationError("Sign in to Instinct in your regular Brave profile first.")
    executable = shutil.which("brave") or shutil.which("brave-browser")
    candidates = [Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")]
    for name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        if os.environ.get(name):
            candidates.append(Path(os.environ[name]) / "BraveSoftware/Brave-Browser/Application/brave.exe")
    executable = executable or next((str(path) for path in candidates if path.is_file()), None)
    if not executable:
        raise MigrationError("Install Brave and sign in to Instinct there before transferring.")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.set_default_timeout(15_000)
            context.add_cookies(cookies)
            page = context.new_page()
            # The app keeps background requests open; network-idle is not readiness.
            # The authenticated vault query below is the actual readiness check.
            try:
                page.goto("https://app.instinct.com/vault", wait_until="domcontentloaded", timeout=30000)
            except Exception:
                raise MigrationError("Instinct did not load. Check the connection and try again before transferring.") from None
            if page.url != "https://app.instinct.com/vault":
                raise MigrationError("The Instinct session is not authenticated.")
            destination = Instinct(page)
            destination.session_fingerprint = hashlib.sha256(cookies[0]["value"].encode()).hexdigest()
            destination.inventory()
            yield destination
        finally:
            browser.close()


class Instinct:
    def __init__(self, page):
        self.page = page

    def call(self, query: str, variables: dict) -> dict:
        try:
            result = self.page.evaluate("""async ({url, query, variables}) => {
              const response = await fetch(url, {
                method: 'POST', credentials: 'include',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query, variables}),
                signal: AbortSignal.timeout(20000)
              });
              return {status: response.status, body: await response.json()};
            }""", {"url": URL, "query": query, "variables": variables})
        except Exception:
            raise MigrationError("Instinct request did not complete; reconcile before retrying any write.") from None
        if result["status"] != 200 or result["body"].get("errors") or not isinstance(result["body"].get("data"), dict):
            raise MigrationError("Instinct rejected the operation; response details withheld to avoid logging credentials.")
        return result["body"]["data"]

    def inventory(self) -> list[dict]:
        data = self.call(VAULT_QUERY, {})
        kinds = {x["kind"]: set(x["subfieldKeys"]) for x in data["vaultKinds"]}
        if not {"username", "password", "totp"} <= kinds.get("login", set()):
            raise MigrationError("Instinct's login contract changed; transfer stopped.")
        return data["vaultEntries"]

    def verify(self, item: Login) -> dict:
        expected_keys = {"username", "password"} | ({"totp"} if item.totp else set())
        matches = [x for x in self.inventory() if x["kind"] == "login" and x["name"] == item.name]
        if len(matches) != 1:
            return {"record": False}
        populated = {x["key"]: bool(x["populated"]) for x in matches[0]["fields"]}
        extra = {key for key, present in populated.items() if present} - expected_keys
        checks = {"no_extra_fields": not extra}
        for key, expected in (("username", item.username), ("password", item.password)):
            if not populated.get(key, False):
                # Instinct rejects reveal requests for unpopulated fields.
                checks[key] = not expected
                continue
            actual = self.call(REVEAL, {"kind": "login", "name": item.name, "key": key})["revealVaultSubfieldValue"]
            checks[key] = actual == expected
        if item.totp:
            if not populated.get("totp", False):
                checks["totp_configuration"] = False
                return checks
            actual = self.call(REVEAL, {"kind": "login", "name": item.name, "key": "totp"})["revealVaultSubfieldValue"]
            try:
                stored = parse_totp(actual)
                checks["totp_configuration"] = stored == item.totp
                # Two different windows, in addition to comparing the complete configuration.
                timestamp = int(time.time())
                checks["totp_codes"] = all(stored.code(t) == item.totp.code(t)
                                           for t in (timestamp, timestamp + item.totp.period))
            except (MigrationError, TypeError):
                checks["totp_configuration"] = False
        return checks

    def transfer(self, item: Login) -> dict:
        # This endpoint is an UPSERT keyed by kind/name: never blindly overwrite.
        inventory = [x for x in self.inventory() if x["kind"] == "login"]
        if item.source_id:
            marker = f" [bw:{item.source_id}]"
            matched = [x for x in inventory if x["name"].casefold().endswith(marker)]
            if matched:
                if len(matched) == 1 and all(self.verify(replace(item, name=matched[0]["name"])).values()):
                    return {"status": "already_present", "verified": True}
                return {"status": "conflict", "verified": False}
            # A record transferred by an older bridge had no marker. Adopt it only
            # when the title and every stored credential match exactly.
            legacy = [x for x in inventory if x["name"] == item.source_name and
                      not re.search(r" \[bw:[0-9a-f-]{36}\]$", x["name"], re.I)]
            if len(legacy) == 1 and all(self.verify(replace(item, name=legacy[0]["name"])).values()):
                return {"status": "already_present", "verified": True}
        existing = [x for x in inventory if x["name"].casefold() == item.name.casefold()]
        if existing:
            if len(existing) == 1 and existing[0]["name"] == item.name and all(self.verify(item).values()):
                return {"status": "already_present", "verified": True}
            return {"status": "conflict", "verified": False}
        try:
            self.call(UPSERT, {"input": {"kind": "login", "name": item.name, "fields": item.fields()}})
        except MigrationError:
            # A timeout can occur after committing the write. No automatic retry.
            return {"status": "uncertain", "verified": False}
        checks = self.verify(item)
        return {"status": "created" if all(checks.values()) else "verification_failed",
                "verified": all(checks.values()), "checks": checks}

    def reload(self):
        self.page.reload(wait_until="domcontentloaded")
