"""Opt-in live test: synthetic fixture -> real Instinct -> read-back -> cleanup.

Run explicitly with --brave-session. Never consumes a real vault export.
"""

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from instinct_bridge.destination import DELETE, brave_session
from instinct_bridge.source import load_plan

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--brave-session", action="store_true", required=True)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
source = load_plan(root / "tests/fixtures/bitwarden-synthetic.json").logins[0]
item = replace(source, name="Instinct Bridge E2E " + uuid4().hex[:12])
report = {"checked_at": datetime.now(timezone.utc).isoformat(), "data": "synthetic",
          "source": "Bitwarden JSON fixture", "destination": "real authenticated Instinct vault"}

with brave_session() as destination:
    assert not any(x["name"] == item.name for x in destination.inventory())
    try:
        report["first_transfer"] = destination.transfer(item)
        assert report["first_transfer"]["status"] == "created", report
        destination.reload()
        report["after_reload"] = destination.verify(item)
        assert all(report["after_reload"].values()), report
        report["second_transfer"] = destination.transfer(item)
        assert report["second_transfer"]["status"] == "already_present", report
        report["conflict"] = destination.transfer(replace(item, password="DIFFERENT-SYNTHETIC-PASSWORD"))
        assert report["conflict"]["status"] == "conflict", report
        report["original_unchanged"] = all(destination.verify(item).values())
        assert report["original_unchanged"], report
    finally:
        # Delete only this unique test record, and only if it still matches its source.
        if all(destination.verify(item).values()):
            destination.call(DELETE, {"kind": "login", "name": item.name})
        report["cleanup_verified"] = not any(x["name"] == item.name for x in destination.inventory())
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n")

assert report["cleanup_verified"], report
print(json.dumps(report, indent=2))
