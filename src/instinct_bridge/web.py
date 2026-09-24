"""Single-user loopback UI. Secrets live only in process memory for 15 minutes."""
import argparse
import atexit
import webbrowser
import hmac
import json
import logging
import secrets
import threading
import time
from contextlib import contextmanager

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.serving import make_server

from .authy import attach_authy, load_authy, match_candidates
from .destination import brave_session
from .source import MigrationError, loads_plan, Plan, Login
from .capture import AuthyCapture

TTL = 900


def create_app(token, expected_host, destination_factory=brave_session, capture_factory=AuthyCapture):
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 35 * 1024 * 1024
    state = {"plan": None, "authy": [], "revision": "", "touched": 0,
             "demo": False, "connection": None}
    lock = threading.Lock()
    origin = "http://" + expected_host
    capture = capture_factory()
    app.extensions["authy_capture"] = capture
    atexit.register(capture.stop, clear=True)

    @app.before_request
    def authenticate():
        if request.host != expected_host:
            return jsonify(error="Invalid host."), 403
        if request.path.startswith("/api/"):
            if not hmac.compare_digest(request.headers.get("X-Bridge-Token", ""), token):
                return jsonify(error="Open the private launch link printed in your terminal."), 403
            if request.headers.get("Origin") != origin:
                return jsonify(error="Cross-origin requests are not allowed."), 403
            if request.method != "POST" or request.mimetype != "application/json":
                return jsonify(error="JSON POST required."), 405
            if not isinstance(request.get_json(), dict):
                return jsonify(error="Expected a JSON object."), 400

    @app.after_request
    def headers(response):
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response

    @app.errorhandler(MigrationError)
    def safe_error(exc):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            return jsonify(error="Request could not be processed."), exc.code
        return jsonify(error="Operation stopped. No secrets were logged. Check the source and reconnect if needed."), 500

    @contextmanager
    def exclusive():
        if not lock.acquire(blocking=False):
            raise MigrationError("Another operation is running. Wait for it to finish.")
        try:
            if state["touched"] and time.monotonic() - state["touched"] > TTL:
                state.update(plan=None, authy=[], revision="", connection=None, demo=False)
            state["touched"] = time.monotonic()
            yield
        finally:
            lock.release()

    def summary():
        plan = state["plan"]
        return {"revision": state["revision"], "demo": state["demo"],
                "accounts": [] if not plan else [{"index": i, "name": x.name, "username": x.username,
                    "has_totp": x.totp is not None, "source_index": x.source_index}
                    for i, x in enumerate(plan.logins)],
                "report": plan.report() if plan else None,
                "authy": [{"id": x.id, "name": x.name, "issuer": x.issuer,
                    "suggestions": match_candidates(x, plan.logins if plan else [])} for x in state["authy"]]}

    @app.get("/")
    def index():
        return send_from_directory(app.root_path + "/static", "index.html")

    @app.get("/static/<path:name>")
    def static_file(name):
        return send_from_directory(app.root_path + "/static", name)

    @app.post("/api/preview")
    def preview():
        payload = request.get_json()
        with exclusive():
            # Failed replacement invalidates the old preview rather than leaving stale secrets actionable.
            state.update(plan=None, authy=[], revision="", connection=None, demo=False)
            raw = payload.get("bitwarden", "")
            if not isinstance(raw, str):
                raise MigrationError("Select a Bitwarden JSON export.")
            authy_raw = capture.encrypted_export() if payload.get("use_capture") is True else payload.get("authy", "")
            accounts = load_authy(authy_raw, payload.get("authy_password", "")) if authy_raw else []
            if raw:
                plan = loads_plan(raw, payload.get("bitwarden_password", ""), allow_partial=True)
            elif accounts:
                # An Authy-only import uses exact per-token identities, without guessing a password match.
                logins = [Login((x.issuer + " — " + x.name) if x.issuer and x.issuer != x.name else x.name,
                                "", "", x.totp, i) for i, x in enumerate(accounts)]
                if len({x.name.casefold() for x in logins}) != len(logins):
                    raise MigrationError("Duplicate Authy names need review; use a Bitwarden export to pair explicitly.")
                plan = Plan(len(logins), logins, [])
                accounts = []  # Keys are already bound to their own standalone entries.
            else:
                raise MigrationError("Choose a Bitwarden export or connect Authy first.")
            state.update(plan=plan, authy=accounts, revision=secrets.token_hex(16))
            if payload.get("use_capture") is True:
                capture.stop(clear=True)
            return jsonify(summary())

    @app.post("/api/demo")
    def demo():
        with exclusive():
            if capture.status()["active"] or capture.status()["count"]:
                raise MigrationError("Finish or cancel iPhone capture before opening sample data.")
            data = {"encrypted": False, "items": [{"type": 1, "name": name,
                "login": {"username": "alex@example.invalid", "password": "SYNTHETIC-demo-only"}}
                for name in ("GitHub", "Figma", "Cloudflare", "Notion")]}
            accounts = load_authy(json.dumps([{"id": "demo-1", "name": "alex@example.invalid",
                "issuer": "GitHub", "decrypted_seed": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", "digits": 6}]))
            state.update(plan=loads_plan(json.dumps(data)), authy=accounts,
                         revision=secrets.token_hex(16), demo=True, connection=None)
            return jsonify(summary())

    @app.post("/api/iphone/start")
    def iphone_start():
        if request.get_json().get("acknowledge_capture") is not True:
            raise MigrationError("Confirm the temporary Authy capture and certificate setup.")
        with exclusive():
            if state["demo"]:
                raise MigrationError("Leave demo mode before connecting an iPhone.")
            return jsonify(capture.start())

    @app.post("/api/iphone/status")
    def iphone_status():
        return jsonify(capture.status())

    @app.post("/api/iphone/finish")
    def iphone_finish():
        with exclusive():
            expected = request.get_json().get("expected_count")
            status = capture.status()
            if type(expected) is not int or expected < 1 or expected != status["count"]:
                raise MigrationError("Confirm the received key count matches the accounts shown in Authy.")
            capture.stop(clear=False)
            return jsonify(capture.status())

    @app.post("/api/iphone/discard")
    def iphone_discard():
        with exclusive():
            capture.stop(clear=True)
            return jsonify(cleared=True)

    @app.post("/api/connect")
    def connect():
        with exclusive():
            if state["demo"]:
                raise MigrationError("Demo mode never connects to a real vault. Load your exports first.")
            with destination_factory() as destination:
                inventory = destination.inventory()
                state["connection"] = getattr(destination, "session_fingerprint", None)
                if state["connection"] is None:
                    raise MigrationError("Could not identify the destination session.")
                return jsonify(connected=True, entries=len(inventory))

    @app.post("/api/transfer")
    def transfer():
        payload = request.get_json()
        with exclusive():
            if state["demo"]:
                raise MigrationError("Demo data cannot be transferred.")
            plan = state["plan"]
            if not plan or not state["revision"] or payload.get("revision") != state["revision"]:
                raise MigrationError("Preview expired or changed. Load your exports again.")
            selected = payload.get("selected")
            if not isinstance(selected, list) or not selected or any(type(i) is not int or not 0 <= i < len(plan.logins) for i in selected) or len(set(selected)) != len(selected):
                raise MigrationError("Select valid, distinct accounts.")
            if payload.get("acknowledge_scope") is not True:
                raise MigrationError("Confirm the transfer scope and selected accounts.")
            mapping = payload.get("mapping", {})
            logins = attach_authy(plan.logins, state["authy"], mapping)
            if set(mapping.values()) - set(selected):
                raise MigrationError("An Authy key is paired with an unselected account.")
            if len(mapping) < len(state["authy"]) and payload.get("acknowledge_unmapped") is not True:
                raise MigrationError("Some Authy keys are unpaired. Pair them or explicitly leave them out.")
            if not state["connection"]:
                raise MigrationError("Connect to Instinct before transferring.")
            results = []
            with destination_factory() as destination:
                if getattr(destination, "session_fingerprint", None) != state["connection"]:
                    state["connection"] = None
                    raise MigrationError("The Instinct session changed. Connect and review the destination again.")
                for i in selected:
                    result = destination.transfer(logins[i])
                    results.append({"index": i, "name": logins[i].name, **result})
                    if not result["verified"]:
                        break
            return jsonify(results=results, not_attempted=len(selected) - len(results),
                           verified=all(x["verified"] for x in results) and len(results) == len(selected))

    @app.post("/api/clear")
    def clear():
        with exclusive():
            state.update(plan=None, authy=[], revision="", connection=None, demo=False)
            capture.stop(clear=True)
        return jsonify(cleared=True)

    @app.post("/api/quit")
    def quit_app():
        with exclusive():
            cleanup = capture.status()["profile_downloaded"]
            state.update(plan=None, authy=[], revision="", connection=None, demo=False)
            capture.stop(clear=True)
            app.config["STOP_EVICTION"] = True
            shutdown = app.config.get("SHUTDOWN")
            if shutdown:
                threading.Timer(0.3, shutdown).start()
            return jsonify(closed=True, phone_cleanup_required=cleanup)

    # Physical eviction, not only eviction on the next request.
    def expire():
        while not app.config.get("STOP_EVICTION"):
            time.sleep(5)
            if lock.acquire(blocking=False):
                try:
                    if state["touched"] and time.monotonic() - state["touched"] > TTL:
                        state.update(plan=None, authy=[], revision="", connection=None, demo=False)
                finally:
                    lock.release()
    threading.Thread(target=expire, daemon=True).start()
    return app


def main():
    parser = argparse.ArgumentParser(description="Start Instinct Bridge on this computer only")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--version", action="version", version="Instinct Bridge 0.3.0")
    parser.add_argument("--open", action="store_true", help="Open the local app in your browser")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535")
    token = secrets.token_urlsafe(32)
    host = f"127.0.0.1:{args.port}"
    app = create_app(token, host)
    logging.getLogger("werkzeug").disabled = True
    server = make_server("127.0.0.1", args.port, app, threaded=True)
    app.config["SHUTDOWN"] = server.shutdown
    launch_url = f"http://{host}/#{token}"
    print(f"Instinct Bridge — open locally: {launch_url}", flush=True)
    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(launch_url)).start()
    if not args.open:
        print("No browser is opened automatically. Ctrl+C stops the app and clears its process memory.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.config["STOP_EVICTION"] = True
        app.extensions["authy_capture"].stop(clear=True)
        server.server_close()
