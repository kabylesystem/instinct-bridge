"""Opt-in real-vault check with two synthetic accounts for one service.

The report contains only booleans and counts. Both synthetic records are removed.
"""

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from instinct_bridge.destination import DELETE, brave_session
from instinct_bridge.source import loads_plan

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--brave-session", action="store_true", required=True)
parser.add_argument("--report", type=Path)
args = parser.parse_args()

run_id = uuid4().hex[:12]
source = {"encrypted": False, "items": [
    {"id": str(uuid4()), "type": 1, "name": f"Instinct Bridge synthetic multi-account {run_id}",
     "login": {"username": username, "password": f"SYNTHETIC-{run_id}-{number}",
               "uris": [{"uri": "https://same-service.example.invalid/login"}]}}
    for number, username in enumerate(("first@example.invalid", "second@example.invalid"), 1)
]}
items = loads_plan(json.dumps(source), allow_partial=True, migration_names=True).logins
assert len(items) == 2 and items[0].site == items[1].site
assert all(f"login: {item.username}" in item.name for item in items)

report = {"checked_at": datetime.now(timezone.utc).isoformat(), "data": "synthetic",
          "same_title_and_service": True, "distinct_source_ids": items[0].source_id != items[1].source_id}
with brave_session() as destination:
    inventory = destination.inventory()
    assert all(not any(entry["kind"] == "login" and entry["name"] == item.name
                       for entry in inventory) for item in items)
    try:
        report["created"] = [destination.transfer(item)["status"] for item in items]
        destination.reload()
        report["exact_readback"] = [all(destination.verify(item).values()) for item in items]
        report["cross_account_mismatch_rejected"] = [
            not all(destination.verify(replace(item, name=other.name)).values())
            for item, other in ((items[0], items[1]), (items[1], items[0]))]
        report["repeat"] = [destination.transfer(item)["status"] for item in items]
        report["vault_entry_count"] = sum(entry["kind"] == "login" and
                                          entry["name"] in {item.name for item in items}
                                          for entry in destination.inventory())
        destination.page.goto("https://app.instinct.com/vault", wait_until="domcontentloaded")
        destination.page.wait_for_timeout(2000)
        visible = destination.page.locator("body").inner_text()
        report["both_labels_visible_in_vault"] = all(item.name in visible for item in items)
        report["both_usernames_visible_in_labels"] = all(item.username in visible for item in items)
    finally:
        for item in items:
            if all(destination.verify(item).values()):
                destination.call(DELETE, {"kind": "login", "name": item.name})
        report["cleanup_verified"] = all(not any(entry["kind"] == "login" and entry["name"] == item.name
                                             for entry in destination.inventory()) for item in items)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n")

assert report["created"] == ["created", "created"] and report["exact_readback"] == [True, True]
assert report["cross_account_mismatch_rejected"] == [True, True]
assert report["repeat"] == ["already_present", "already_present"] and report["vault_entry_count"] == 2
assert report["both_labels_visible_in_vault"] and report["both_usernames_visible_in_labels"]
assert report["cleanup_verified"]
print(json.dumps(report, indent=2))
