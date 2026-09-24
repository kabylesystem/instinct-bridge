import base64
import importlib.util
import json
import plistlib
from pathlib import Path
from types import SimpleNamespace
import unittest
import urllib.request
import urllib.error
from urllib.parse import urlencode

from instinct_bridge.capture import AuthyCapture, CaptureAddon, capture_tokens

FIXTURES = Path(__file__).parent / 'fixtures'
TOKEN = json.loads((FIXTURES/'authy-encrypted-synthetic.json').read_text())['authenticator_tokens'][0]

class CaptureParsingTests(unittest.TestCase):
    def test_encrypted_response_whitelists_fields(self):
        body=json.dumps({'authenticator_tokens':[{**TOKEN,'auth_token':'private-session','decrypted_seed':'must-not-retain'}],'device_secret':'must-not-retain'}).encode()
        result=capture_tokens('api.authy.com','/json/authenticator_tokens','GET','application/json',body,response=True)
        self.assertEqual(result,[TOKEN])
        self.assertNotIn('private-session',json.dumps(result))
        self.assertNotIn('must-not-retain',json.dumps(result))

    def test_update_form_and_duplicates(self):
        doc={**TOKEN,'token_id':TOKEN['unique_id'],'auth_token':'not-retained'}
        doc.pop('unique_id')
        body=urlencode(doc).encode()
        result=capture_tokens('api.authy.com','/json/authenticator_tokens/update','POST','application/x-www-form-urlencoded',body)
        self.assertEqual(result,[TOKEN])
        self.assertEqual(capture_tokens('api.authy.com','/json/authenticator_tokens/update','POST','application/x-www-form-urlencoded',body+b'&token_id=other'),[])

    def test_other_hosts_paths_and_oversize_are_ignored(self):
        body=json.dumps({'authenticator_tokens':[TOKEN]}).encode()
        for host,path in [('api.authy.com.evil.invalid','/json/authenticator_tokens'),('evil.invalid','/json/authenticator_tokens'),('api.authy.com','/unrelated'),('api.authy.com','/json/authenticator_tokens/other')]:
            self.assertEqual(capture_tokens(host,path,'GET','application/json',body,response=True),[])
        self.assertEqual(capture_tokens('api.authy.com','/json/authenticator_tokens','GET','application/json',b' '*(5*1024*1024+1),response=True),[])

    def test_unpaired_clients_and_other_upstreams_rejected(self):
        capture=AuthyCapture();capture.active=True;capture.phone_ip='192.168.1.5'
        addon=CaptureAddon(capture)
        other=SimpleNamespace(peername=('192.168.1.6',123),error=None)
        addon.client_connected(other)
        self.assertIsNotNone(other.error)
        server=SimpleNamespace(server=SimpleNamespace(address=('example.com',443),error=None))
        addon.server_connect(server)
        self.assertIsNotNone(server.server.error)

    def test_failed_upstream_and_unpaired_response_never_captured(self):
        capture=AuthyCapture();capture.active=True;capture.phone_ip='192.168.1.5'
        addon=CaptureAddon(capture)
        flow=SimpleNamespace(client_conn=SimpleNamespace(peername=('192.168.1.5',123)),
            request=SimpleNamespace(host='api.authy.com',scheme='https',path='/json/authenticator_tokens',method='GET',headers={},content=b''),
            response=SimpleNamespace(status_code=500,headers={'content-type':'application/json'},content=json.dumps({'authenticator_tokens':[TOKEN]}).encode()))
        addon.response(flow);self.assertFalse(capture.tokens)
        flow.response.status_code=200;flow.client_conn.peername=('192.168.1.6',123)
        addon.response(flow);self.assertFalse(capture.tokens)
        flow.client_conn.peername=('192.168.1.5',123)
        addon.response(flow);self.assertEqual(len(capture.tokens),1)
        self.assertNotIn(TOKEN['encrypted_seed'],json.dumps(capture.status()))

@unittest.skipUnless(importlib.util.find_spec('mitmproxy') and importlib.util.find_spec('qrcode'), 'optional iPhone runtime')
class CaptureWireTests(unittest.TestCase):
    def test_pairing_profile_blocked_proxy_and_cleanup(self):
        capture=AuthyCapture()
        try:
            status=capture.start(address='127.0.0.1')
            temp=Path(capture.temp.name)
            self.assertEqual(temp.stat().st_mode & 0o777,0o700)
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(status['setup_url']+'wrong')
            self.assertIsNone(capture.phone_ip)
            with urllib.request.urlopen(status['setup_url']+'/profile') as response:
                profile=plistlib.loads(response.read())
            self.assertEqual(capture.phone_ip,'127.0.0.1')
            self.assertEqual(profile['PayloadContent'][0]['PayloadType'],'com.apple.security.root')
            self.assertNotIn(b'PRIVATE KEY',profile['PayloadContent'][0]['PayloadContent'])
            # This must be rejected before any DNS/upstream connection.
            import http.client
            connection=http.client.HTTPConnection('127.0.0.1',status['port'],timeout=5)
            connection.set_tunnel('example.invalid',443)
            with self.assertRaisesRegex(OSError,'403'):
                connection.connect()
            connection.close()
        finally:
            capture.stop(clear=True)
        self.assertFalse(temp.exists())
        self.assertFalse(capture.active)
        self.assertFalse(capture.tokens)
