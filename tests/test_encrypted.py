import json
from pathlib import Path
import unittest

from instinct_bridge.authy import load_authy, attach_authy, match_candidates
from instinct_bridge.source import Login, MigrationError, load_plan, loads_plan, parse_totp

FIXTURES = Path(__file__).parent / 'fixtures'
PASSWORD = 'SYNTHETIC-export-password'
SEED = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'

class EncryptedTests(unittest.TestCase):
    def test_independent_node_bitwarden_fixtures(self):
        for kind in ('pbkdf2', 'argon2'):
            with self.subTest(kind=kind):
                plan = load_plan(FIXTURES / f'bitwarden-{kind}-synthetic.json', PASSWORD)
                self.assertEqual(plan.logins[0].password, 'SYNTHETIC-account-password')
                self.assertIsNone(plan.logins[0].totp)
                self.assertNotIn('SYNTHETIC-account-password', repr(plan))

    def test_wrong_password_and_tampered_mac(self):
        raw = (FIXTURES / 'bitwarden-pbkdf2-synthetic.json').read_text()
        with self.assertRaisesRegex(MigrationError, 'Wrong export password'):
            loads_plan(raw, 'wrong')
        doc = json.loads(raw)
        doc['data'] = doc['data'][:-8] + 'AAAAAAAA'
        with self.assertRaisesRegex(MigrationError, 'damaged'):
            loads_plan(json.dumps(doc), PASSWORD)

    def test_kdf_limits_and_account_restricted(self):
        doc = json.loads((FIXTURES / 'bitwarden-argon2-synthetic.json').read_text())
        for field, value in [('kdfMemory', 1000000), ('kdfIterations', True), ('kdfParallelism', 999)]:
            with self.subTest(field=field), self.assertRaises(MigrationError):
                loads_plan(json.dumps({**doc, field:value}), PASSWORD)
        with self.assertRaisesRegex(MigrationError, 'account-restricted'):
            loads_plan(json.dumps({**doc, 'passwordProtected':False}), PASSWORD)

    def test_independent_authy_fixtures(self):
        for filename in ('authy-encrypted-synthetic.json', 'authy-zero-iv-synthetic.json'):
            raw = (FIXTURES / filename).read_text()
            account = load_authy(raw, PASSWORD)[0]
            self.assertEqual(account.totp.secret, SEED)
            self.assertNotIn(SEED, repr(account))
            with self.assertRaises(MigrationError):
                load_authy(raw, 'wrong')

    def test_reject_nonstandard_uri_and_metadata(self):
        for overrides in ({'decrypted_seed':f'otpauth://totp/test?secret={SEED}&digits=8'}, {'digits':8}, {'algorithm':None}, {'period':60}):
            with self.subTest(overrides=overrides), self.assertRaises(MigrationError):
                load_authy(json.dumps([{'name':'Synthetic', 'decrypted_seed':SEED, **overrides}]))

    def test_mapping_conflicts_and_ambiguity(self):
        accounts = load_authy(json.dumps([{'id':'a','name':'same@example.invalid','issuer':'GitHub','decrypted_seed':SEED}]))
        logins = [Login('GitHub','same@example.invalid','fake'), Login('Other','same@example.invalid','fake')]
        self.assertEqual(match_candidates(accounts[0], logins), [0])
        accounts[0].issuer = 'Unknown'
        self.assertEqual(match_candidates(accounts[0], logins), [0,1])
        mapped = attach_authy(logins, accounts, {'a':0})
        self.assertIsNone(logins[0].totp)
        self.assertEqual(mapped[0].totp.secret, SEED)
        logins[0].totp = parse_totp('JBSWY3DPEHPK3PXP')
        with self.assertRaisesRegex(MigrationError, 'different keys'):
            attach_authy(logins, accounts, {'a':0})
        for mapping in ({'a':True}, {'missing':0}, {'a':-1}):
            with self.assertRaises(MigrationError):
                attach_authy(logins, accounts, mapping)

    def test_partial_scope_is_visible(self):
        raw = json.dumps({'encrypted':False,'items':[{'type':1,'name':'Synthetic','notes':'private-note','login':{'password':'fake','uris':[{'uri':'https://example.invalid'}]}}]})
        self.assertEqual(loads_plan(raw).logins, [])
        partial = loads_plan(raw, allow_partial=True)
        self.assertEqual(len(partial.logins), 1)
        self.assertTrue(partial.issues[0]['partial'])
        self.assertNotIn('private-note', json.dumps(partial.report()))
