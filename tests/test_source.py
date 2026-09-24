import copy
import json
import tempfile
import unittest
from pathlib import Path

from instinct_bridge.source import MigrationError, load_plan, parse_totp

FIXTURE = Path(__file__).parent / "fixtures" / "bitwarden-synthetic.json"
SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


class SourceTests(unittest.TestCase):
    def plan(self, data):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "synthetic.json"
            path.write_text(json.dumps(data))
            return load_plan(path)

    def data(self):
        return json.loads(FIXTURE.read_text())

    def test_fixture_and_secret_free_report(self):
        plan = load_plan(FIXTURE)
        self.assertEqual(len(plan.logins), 1)
        self.assertEqual(plan.issues, [])
        for secret in (SECRET, plan.logins[0].password, plan.logins[0].username):
            self.assertNotIn(secret, json.dumps(plan.report()))
            self.assertNotIn(secret, repr(plan))
            self.assertNotIn(secret, repr(plan.logins[0]))

    def test_rfc6238_sha1_vectors(self):
        config = parse_totp(f"otpauth://totp/test?secret={SECRET}&digits=8")
        for timestamp, expected in ((59, "94287082"), (1111111109, "07081804"),
                                    (1111111111, "14050471"), (1234567890, "89005924"),
                                    (2000000000, "69279037"), (20000000000, "65353130")):
            self.assertEqual(config.code(timestamp), expected)

    def test_normalized_instinct_uri_equivalent(self):
        self.assertEqual(parse_totp(SECRET), parse_totp(
            f"otpauth://totp/login?algorithm=SHA1&digits=6&period=30&secret={SECRET}"))

    def test_unsupported_otp_is_not_coerced(self):
        for value in ("steam://ABC", f"otpauth://hotp/test?secret={SECRET}&counter=1",
                      f"otpauth://totp/test?secret={SECRET}&digits=7",
                      f"otpauth://totp/test?secret={SECRET}&period=0",
                      f"otpauth://totp/test?secret={SECRET}&secret={SECRET}"):
            with self.assertRaises(MigrationError):
                parse_totp(value)

    def test_nondefault_destination_parameters_withheld(self):
        data = self.data()
        data["items"][0]["login"]["totp"] = data["items"][0]["login"]["totp"].replace("&digits=6", "&digits=8")
        plan = self.plan(data)
        self.assertFalse(plan.logins)
        self.assertTrue(plan.issues)

    def test_notes_urls_and_passkeys_are_not_silently_dropped(self):
        for key, value in (("notes", "sensitive note"), ("fields", [{"name": "private", "value": "private"}])):
            data = self.data()
            data["items"][0][key] = value
            plan = self.plan(data)
            self.assertFalse(plan.logins)
            self.assertTrue(plan.issues)
        for key in ("uris", "fido2Credentials"):
            data = self.data()
            data["items"][0]["login"][key] = [{"value": "sensitive"}]
            self.assertFalse(self.plan(data).logins)

    def test_duplicate_names_fail_before_transfer(self):
        data = self.data()
        data["items"].append(copy.deepcopy(data["items"][0]))
        data["items"][1]["name"] = data["items"][1]["name"].lower()
        with self.assertRaises(MigrationError):
            self.plan(data)

    def test_encrypted_export_fails_closed(self):
        with self.assertRaises(MigrationError):
            self.plan({"encrypted": True, "data": "not-plaintext"})

    def test_unknown_item_and_bad_field_type(self):
        data = self.data()
        data["items"][0]["type"] = 2
        self.assertTrue(self.plan(data).issues)
        data = self.data()
        data["items"][0]["login"]["username"] = False
        self.assertTrue(self.plan(data).issues)

    def test_authenticator_only_export(self):
        data = self.data()
        del data["items"][0]["login"]["password"]
        plan = self.plan(data)
        self.assertEqual(len(plan.logins), 1)
        self.assertEqual(plan.logins[0].password, "")


if __name__ == "__main__":
    unittest.main()
