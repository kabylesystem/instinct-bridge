"""The default command previews locally; explicit flags enable network writes."""

import argparse
import getpass
import json
from pathlib import Path

from .source import MigrationError, load_plan


def main():
    parser = argparse.ArgumentParser(description="Local Bitwarden login/TOTP migration prototype")
    parser.add_argument("export", type=Path)
    parser.add_argument("--encrypted", action="store_true", help="Prompt privately for the portable export password")
    parser.add_argument("--apply", action="store_true", help="Transfer ready records to Instinct")
    parser.add_argument("--brave-session", action="store_true", help="Read only the local Instinct session from Brave")
    parser.add_argument("--accept-unofficial-connector", action="store_true", help="Acknowledge the observed private web API")
    args = parser.parse_args()
    try:
        password = getpass.getpass("Bitwarden export password: ") if args.encrypted else ""
        plan = load_plan(args.export, password)
        password = ""
        report = plan.report()
        if args.apply:
            if not args.brave_session or not args.accept_unofficial_connector:
                raise MigrationError("Transfer requires --brave-session and --accept-unofficial-connector.")
            if plan.issues:
                print(json.dumps(report, indent=2))
                raise MigrationError("Unresolved source items; no records transferred. Resolve or explicitly prepare a supported subset.")
            from .destination import brave_session
            with brave_session() as destination:
                report["results"] = []
                for index, item in enumerate(plan.logins):
                    result = destination.transfer(item)
                    report["results"].append({"index": index, **result})
                    if not result["verified"]:
                        break
                report["not_attempted"] = len(plan.logins) - len(report["results"])
            print(json.dumps(report, indent=2))
            return 0 if not report["not_attempted"] and all(x["verified"] for x in report["results"]) else 2
        print(json.dumps(report, indent=2))
        return 0 if not plan.issues else 2
    except MigrationError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    except Exception:
        # Playwright/library exceptions may include request payloads or sensitive paths.
        print(json.dumps({"error": "Operation stopped. No raw exception logged; reconcile destination before retrying."}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
