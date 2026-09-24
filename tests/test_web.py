from contextlib import contextmanager
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from instinct_bridge.web import create_app

FIXTURES = Path(__file__).parent / 'fixtures'
class WebTests(unittest.TestCase):
    def setUp(self):
        self.fingerprint = 'synthetic-session'
        self.writes = []
        outer = self
        class Destination:
            def inventory(self): return []
            def transfer(self, item):
                outer.writes.append(item)
                return {'status':'created','verified':True}
        @contextmanager
        def factory():
            destination = Destination()
            destination.session_fingerprint = self.fingerprint
            yield destination
        self.app = create_app('synthetic-token', '127.0.0.1:8765', factory)
        self.client = self.app.test_client()
        self.headers = {'Origin':'http://127.0.0.1:8765', 'X-Bridge-Token':'synthetic-token'}

    def tearDown(self): self.app.config['STOP_EVICTION'] = True

    def post(self, path, data=None, headers=None):
        return self.client.post('/api/'+path, json=data if data is not None else {}, base_url='http://127.0.0.1:8765', headers=self.headers if headers is None else headers)

    def preview(self, authy=False):
        result = self.post('preview', {'bitwarden':(FIXTURES/'bitwarden-pbkdf2-synthetic.json').read_text(), 'bitwarden_password':'SYNTHETIC-export-password', 'authy':(FIXTURES/'authy-encrypted-synthetic.json').read_text() if authy else '', 'authy_password':'SYNTHETIC-export-password'})
        self.assertEqual(result.status_code, 200)
        for secret in ('SYNTHETIC-account-password','SYNTHETIC-export-password','GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'):
            self.assertNotIn(secret, result.get_data(as_text=True))
        return result.json['revision']

    def transfer_payload(self, revision_value, **overrides):
        return {'revision':revision_value,'selected':[0],'mapping':{},'acknowledge_scope':True,**overrides}

    def test_token_origin_host_and_body_protection(self):
        for headers in ({}, {'Origin':'http://evil.invalid','X-Bridge-Token':'synthetic-token'}, {'Origin':'http://127.0.0.1:8765','X-Bridge-Token':'wrong'}):
            self.assertEqual(self.post('demo', headers=headers).status_code, 403)
        self.assertEqual(self.client.get('/', base_url='http://evil.invalid').status_code, 403)
        self.assertEqual(self.post('demo', []).status_code, 400)
        response = self.client.get('/', base_url='http://127.0.0.1:8765')
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
        response.close()

    def test_demo_never_connects_or_transfers(self):
        revision = self.post('demo').json['revision']
        self.assertEqual(self.post('connect').status_code, 400)
        self.assertEqual(self.post('transfer',self.transfer_payload(revision)).status_code, 400)
        self.assertEqual(self.writes, [])

    def test_encrypted_preview_pair_transfer_and_clear(self):
        revision = self.preview(True)
        self.assertEqual(self.post('connect').status_code, 200)
        payload = self.transfer_payload(revision, mapping={'synthetic-authy-1':0})
        self.assertTrue(self.post('transfer',payload).json['verified'])
        self.assertEqual(self.writes[0].totp.secret,'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ')
        self.post('clear')
        self.assertEqual(self.post('transfer',payload).status_code, 400)

    def test_scope_mapping_and_selection_guards(self):
        revision = self.preview(True)
        self.post('connect')
        for overrides in ({}, {'acknowledge_scope':False}, {'selected':[True]}, {'selected':[0,0]}, {'selected':[]}, {'revision':'stale'}, {'mapping':{'synthetic-authy-1':9}}):
            self.assertEqual(self.post('transfer', self.transfer_payload(revision, **overrides)).status_code,400)
        self.assertEqual(self.writes, [])
        self.assertTrue(self.post('transfer',self.transfer_payload(revision, acknowledge_unmapped=True)).json['verified'])

    def test_destination_session_change_blocks_writes(self):
        revision = self.preview()
        self.post('connect')
        self.fingerprint = 'different-user-session'
        result = self.post('transfer',self.transfer_payload(revision))
        self.assertEqual(result.status_code,400)
        self.assertIn('session changed', result.json['error'])
        self.assertEqual(self.writes, [])

    def test_expiry_and_failed_preview_invalidate_old_revision(self):
        revision = self.preview()
        self.post('connect')
        with patch('instinct_bridge.web.time.monotonic', return_value=10**15):
            self.assertEqual(self.post('transfer',self.transfer_payload(revision)).status_code,400)
        revision = self.preview()
        self.assertEqual(self.post('preview',{'bitwarden':'broken'}).status_code,400)
        self.assertEqual(self.post('transfer',self.transfer_payload(revision)).status_code,400)
        self.assertEqual(self.writes, [])

    def test_authy_only_preview_binds_keys_without_guessing(self):
        result=self.post('preview',{'authy':(FIXTURES/'authy-encrypted-synthetic.json').read_text(),'authy_password':'SYNTHETIC-export-password'})
        self.assertEqual(result.status_code,200)
        self.assertTrue(result.json['accounts'][0]['has_totp'])
        self.assertEqual(result.json['authy'],[])
        self.post('connect')
        result=self.post('transfer',self.transfer_payload(result.json['revision']))
        self.assertTrue(result.json['verified'])
        self.assertEqual(self.writes[0].password,'')
        self.assertIsNotNone(self.writes[0].totp)

    def test_iphone_start_requires_explicit_capture_action(self):
        result=self.post('iphone/start')
        self.assertEqual(result.status_code,400)
        self.assertFalse(self.app.extensions['authy_capture'].active)

    def test_iphone_status_is_private_and_finish_requires_count(self):
        capture=self.app.extensions['authy_capture']
        token=json.loads((FIXTURES/'authy-encrypted-synthetic.json').read_text())['authenticator_tokens'][0]
        capture.tokens[token['unique_id']]=token
        status=self.post('iphone/status')
        self.assertEqual(status.json['count'],1)
        self.assertNotIn(token['encrypted_seed'],status.get_data(as_text=True))
        self.assertEqual(self.post('iphone/finish',{'expected_count':2}).status_code,400)
        self.assertEqual(self.post('iphone/finish',{'expected_count':1}).status_code,200)
        result=self.post('preview',{'use_capture':True,'authy_password':'SYNTHETIC-export-password'})
        self.assertEqual(result.status_code,200)
        self.assertEqual(capture.tokens,{})

    def test_wrong_capture_password_preserves_retry_input(self):
        capture=self.app.extensions['authy_capture']
        token=json.loads((FIXTURES/'authy-encrypted-synthetic.json').read_text())['authenticator_tokens'][0]
        capture.tokens[token['unique_id']]=token
        self.assertEqual(self.post('preview',{'use_capture':True,'authy_password':'wrong'}).status_code,400)
        self.assertEqual(len(capture.tokens),1)
        self.post('clear')
        self.assertEqual(capture.tokens,{})

    def test_quit_clears_loaded_keys_and_reminds_phone_cleanup(self):
        revision = self.preview(True)
        capture = self.app.extensions['authy_capture']
        capture.tokens['test'] = {'encrypted_seed': 'private-test-value'}
        capture.profile_downloaded = True
        response = self.post('quit')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['phone_cleanup_required'])
        self.assertEqual(capture.tokens, {})
        self.assertTrue(self.app.config['STOP_EVICTION'])
        self.assertEqual(self.post('transfer', self.transfer_payload(revision)).status_code, 400)

    def test_demo_cannot_hide_pending_iphone_capture(self):
        capture = self.app.extensions['authy_capture']
        capture.tokens['test'] = {'encrypted_seed': 'private-test-value'}
        self.assertEqual(self.post('demo').status_code, 400)
        self.assertIn('test', capture.tokens)
        self.post('iphone/discard')
        self.assertEqual(self.post('demo').status_code, 200)
