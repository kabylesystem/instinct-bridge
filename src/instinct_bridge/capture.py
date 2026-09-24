"""Opt-in, short-lived Authy-only capture. No traffic archives or plaintext exports."""
import asyncio
import base64
import html
import ipaddress
import json
import logging
import plistlib
import re
import secrets
import socket
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from .source import MigrationError, _unique_object

LIMIT = 5 * 1024 * 1024
ENDPOINT = re.compile(r"/(?:[^/?]+/)*authenticator_tokens(?:/update)?/?$")
FIELDS = {"unique_id", "name", "issuer", "digits", "algorithm", "period",
          "encrypted_seed", "salt", "key_derivation_iterations", "unique_iv"}


def capture_tokens(host, path, method, content_type, body, response=False):
    """Retain only encrypted tokens from the exact Authy host and token endpoints."""
    if host != "api.authy.com" or not ENDPOINT.fullmatch(urlsplit(path).path) or len(body) > LIMIT:
        return []
    try:
        if response:
            doc = json.loads(body, object_pairs_hook=_unique_object)
            tokens = doc.get("authenticator_tokens", []) if isinstance(doc, dict) else []
        elif method == "POST" and urlsplit(path).path.rstrip('/').endswith('/update') and content_type.split(';')[0] == "application/x-www-form-urlencoded":
            fields = parse_qs(body.decode(), keep_blank_values=True, max_num_fields=80)
            if any(len(v) != 1 for v in fields.values()):
                return []
            token = {k: v[0] for k, v in fields.items() if k in FIELDS}
            token["unique_id"] = fields.get("token_id", [""])[0]
            for key, default in (("digits", 6), ("key_derivation_iterations", 100000)):
                token[key] = int(token.get(key, default))
            tokens = [token]
        else:
            return []
        if not isinstance(tokens, list) or len(tokens) > 1000:
            return []
        clean = []
        for token in tokens:
            if not isinstance(token, dict):
                continue
            item = {key: value for key, value in token.items() if key in FIELDS}
            if not all(isinstance(item.get(k), str) and item[k] for k in ('unique_id', 'name', 'encrypted_seed', 'salt')):
                continue
            if any(isinstance(v, (list, dict)) for v in item.values()) or len(json.dumps(item)) > 16384:
                continue
            base64.b64decode(item['encrypted_seed'], validate=True)
            clean.append(item)
        return clean
    except (ValueError, TypeError, UnicodeError, MigrationError, RecursionError):
        return []


def local_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(('1.1.1.1', 80))  # Route selection only; no packet is sent.
            address = sock.getsockname()[0]
        except OSError:
            raise MigrationError("Connect this computer and the iPhone to the same trusted Wi-Fi.") from None
    ip = ipaddress.ip_address(address)
    if not ip.is_private or ip.is_loopback or ip.is_link_local:
        raise MigrationError("A private Wi-Fi/LAN address is required for iPhone capture.")
    return address


class AuthyCapture:
    """One explicitly paired client, one exact upstream host, a 15-minute lifetime."""
    def __init__(self):
        self.lock = threading.RLock()
        self.master = None
        self.thread = None
        self.server = None
        self.temp = None
        self.active = False
        self.phone_ip = None
        self.tokens = {}
        self.error = None
        self.trusted = False
        self.profile_downloaded = False
        self.started = 0
        self.address = None
        self.proxy_port = 0
        self.setup_url = None
        self.profile_id = None
        self.certificate_name = None
        self.certificate_der = None
        self.qr = None
        self.ready = threading.Event()
        self.timer = None

    def start(self, address=None):
        if not self.active:
            self.stop(clear=True)
        with self.lock:
            if self.active:
                return self.status()
            try:
                from mitmproxy.certs import CertStore
                import qrcode
                from qrcode.image.svg import SvgPathImage
            except ImportError:
                raise MigrationError("Use the desktop download with iPhone support, or install the [iphone] extra with Python 3.12+.") from None
            self.address = address or local_address()
            if not ipaddress.ip_address(self.address).is_private:
                raise MigrationError("Capture must use a private local address.")
            self.phone_ip = None
            self.trusted = self.profile_downloaded = False
            self.error = None
            self.started = time.monotonic()
            self.ready.clear()
            self.nonce = secrets.token_urlsafe(24)
            suffix = uuid4().hex
            self.profile_id = 'community.instinctbridge.capture.' + suffix
            self.certificate_name = 'Instinct Bridge ' + suffix[:8]
            # Linux uses RAM-backed storage. Other platforms use a private temp directory.
            self.temp = tempfile.TemporaryDirectory(prefix='instinct-bridge-', dir='/dev/shm' if Path('/dev/shm').is_dir() else None)
            directory = Path(self.temp.name)
            directory.chmod(0o700)
            CertStore.create_store(directory, 'mitmproxy', 2048, organization='Instinct Bridge', cn=self.certificate_name)
            from cryptography import x509
            from cryptography.hazmat.primitives.serialization import Encoding
            self.certificate_der = x509.load_pem_x509_certificate((directory/'mitmproxy-ca-cert.pem').read_bytes()).public_bytes(Encoding.DER)
            with socket.socket() as probe:
                probe.bind((self.address, 0))
                self.proxy_port = probe.getsockname()[1]
            manager = self
            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass
                def do_GET(self):
                    if self.headers.get('Host') != f'{manager.address}:{manager.server.server_port}':
                        self.send_error(403)
                        return
                    if self.path not in (f'/{manager.nonce}', f'/{manager.nonce}/profile') or not manager.active:
                        self.send_error(404)
                        return
                    ip = self.client_address[0]
                    with manager.lock:
                        if manager.phone_ip not in (None, ip):
                            self.send_error(403)
                            return
                        if self.path.endswith('/profile'):
                            manager.phone_ip = ip
                            manager.profile_downloaded = True
                            body = manager.profile()
                            content_type = 'application/x-apple-aspen-config'
                        else:
                            body = manager.phone_page().encode()
                            content_type = 'text/html; charset=utf-8'
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'")
                    self.end_headers()
                    self.wfile.write(body)
            self.server = ThreadingHTTPServer((self.address, 0), Handler)
            self.server.daemon_threads = True
            self.setup_url = f'http://{self.address}:{self.server.server_port}/{self.nonce}'
            self.qr = 'data:image/svg+xml;base64,' + base64.b64encode(qrcode.make(self.setup_url, image_factory=SvgPathImage).to_string()).decode()
            self.active = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
        if not self.ready.wait(12) or self.error:
            self.stop(clear=True)
            raise MigrationError("Could not start the local Authy capture. Check the local network and optional dependencies.")
        self.timer = threading.Timer(900, lambda: self.stop(clear=True))
        self.timer.daemon = True
        self.timer.start()
        return self.status()

    def _run(self):
        async def run():
            from mitmproxy.options import Options
            from mitmproxy.tools.dump import DumpMaster
            logger = logging.getLogger('mitmproxy')
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
            options = Options(listen_host=self.address, listen_port=self.proxy_port, confdir=self.temp.name,
                              ssl_insecure=False, http2=False)
            self.master = DumpMaster(options, with_termlog=False, with_dumper=False)
            self.master.options.update(connection_strategy='lazy', body_size_limit='5m',
                                       keep_host_header=False, upstream_cert=False)
            self.master.addons.add(CaptureAddon(self))
            await self.master.run()
        try:
            asyncio.run(run())
        except Exception:
            self.error = 'Capture stopped unexpectedly. Remove the iPhone proxy before continuing.'
            self.ready.set()

    def profile(self):
        cert_uuid = str(uuid4())
        return plistlib.dumps({'PayloadType':'Configuration', 'PayloadVersion':1,
            'PayloadIdentifier':self.profile_id, 'PayloadUUID':str(uuid4()),
            'PayloadDisplayName':self.certificate_name,
            'PayloadDescription':'Temporary certificate for local Authy transfer. Remove after capture.',
            'PayloadRemovalDisallowed':False, 'PayloadContent':[{
                'PayloadType':'com.apple.security.root', 'PayloadVersion':1,
                'PayloadIdentifier':self.profile_id+'.certificate', 'PayloadUUID':cert_uuid,
                'PayloadDisplayName':self.certificate_name, 'PayloadContent':self.certificate_der}]})

    def phone_page(self):
        name = html.escape(self.certificate_name)
        return f'''<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Connect Authy</title><style>body{{background:#0c1118;color:#eff4fa;font:17px/1.6 sans-serif;padding:24px;max-width:700px}}a{{color:#77afff}}li{{margin:18px 0}}code{{color:#77afff}}</style><h1>Connect Authy</h1><p>This temporary certificate lets this computer read Authy sync traffic. Use a trusted Wi-Fi. Only api.authy.com is accepted by the proxy; other traffic is blocked while it is selected.</p><ol><li><a href="/{self.nonce}/profile">Download {name}</a>, then Settings → Profile Downloaded → Install.</li><li>Settings → General → About → Certificate Trust Settings: enable <strong>{name}</strong>.</li><li>Settings → Wi-Fi → ⓘ → Configure Proxy → Manual. Server: <code>{self.address}</code>, port: <code>{self.proxy_port}</code>. Authentication off. Save.</li><li>Open Authy → Settings → Accounts. To request a sync, touch the backups switch, then choose <strong>Don't Disable</strong> at the confirmation. Never confirm Disable. If that choice is absent, stop and return to the computer.</li></ol><p>The computer displays how many keys arrived. Compare that count with Authy before continuing.</p><h2>After capture</h2><p>Set the Wi-Fi proxy to Off, then remove <strong>{name}</strong> under Settings → General → VPN &amp; Device Management. Keep Authy installed.</p></html>'''

    def status(self):
        with self.lock:
            return {'active':self.active, 'count':len(self.tokens), 'phone_paired':bool(self.phone_ip),
                    'tls_seen':self.trusted, 'profile_downloaded':self.profile_downloaded,
                    'error':self.error, 'setup_url':self.setup_url if self.active else None,
                    'qr':self.qr if self.active else None, 'certificate_name':self.certificate_name,
                    'server':self.address, 'port':self.proxy_port}

    def encrypted_export(self):
        with self.lock:
            if not self.tokens:
                raise MigrationError("No Authy keys received yet. Complete the phone steps first.")
            return json.dumps({'authenticator_tokens':list(self.tokens.values())})

    def stop(self, clear=False):
        # Do not hold self.lock while joining the worker: a hook may own it.
        self.active = False
        if self.timer:
            self.timer.cancel()
            self.timer = None
        if self.master:
            self.master.shutdown()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=5)
        self.master = None
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.temp:
            self.temp.cleanup()
            self.temp = None
        if clear:
            self.tokens.clear()
        self.qr = self.setup_url = None


class CaptureAddon:
    def __init__(self, manager):
        self.manager = manager

    def running(self):
        self.manager.ready.set()

    def client_connected(self, client):
        if not self.manager.active or client.peername[0] != self.manager.phone_ip:
            client.error = 'Only the paired iPhone may connect.'

    def server_connect(self, data):
        if data.server.address != ("api.authy.com", 443):
            data.server.error = "Only the Authy upstream is allowed."

    def http_connect(self, flow):
        from mitmproxy import http
        if flow.request.host != 'api.authy.com' or flow.request.port != 443:
            flow.response = http.Response.make(403, b'Only Authy traffic is allowed.')

    def requestheaders(self, flow):
        from mitmproxy import http
        if flow.request.host != 'api.authy.com' or flow.request.scheme != 'https' or flow.request.port != 443:
            flow.response = http.Response.make(403, b'Only Authy traffic is allowed.')

    def response(self, flow):
        if not self.manager.active or flow.client_conn.peername[0] != self.manager.phone_ip or not 200 <= flow.response.status_code < 300:
            return
        if flow.request.host != 'api.authy.com' or flow.request.scheme != 'https':
            return
        # A successful response from the verified upstream confirms the TLS path.
        self.manager.trusted = True
        tokens = capture_tokens(flow.request.host, flow.request.path, flow.request.method,
                                flow.request.headers.get('content-type',''), flow.request.content or b'')
        tokens += capture_tokens(flow.request.host, flow.request.path, flow.request.method,
                                 flow.response.headers.get('content-type',''), flow.response.content or b'', response=True)
        with self.manager.lock:
            for token in tokens:
                if token['unique_id'] in self.manager.tokens or len(self.manager.tokens) < 1000:
                    self.manager.tokens[token['unique_id']] = token
