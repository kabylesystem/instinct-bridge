import unittest
from dataclasses import replace

from instinct_bridge.destination import Instinct, UPSERT, REVEAL
from instinct_bridge.source import Login, MigrationError


class FakeDestination(Instinct):
    def __init__(self, entries=(), verified=True, write_error=False):
        self.entries = list(entries)
        self.verified = verified
        self.write_error = write_error
        self.writes = 0

    def inventory(self):
        return self.entries

    def verify(self, item):
        return {"password": self.verified}

    def call(self, query, variables):
        if query == UPSERT:
            self.writes += 1
            if self.write_error:
                raise MigrationError("Synthetic lost response")
        return {}


class DestinationTests(unittest.TestCase):
    def setUp(self):
        self.item = Login("SYNTHETIC", "test@example.invalid", "fake")

    def test_existing_matching_record_is_not_written_again(self):
        destination = FakeDestination([{"kind": "login", "name": "SYNTHETIC"}])
        self.assertEqual(destination.transfer(self.item)["status"], "already_present")
        self.assertEqual(destination.writes, 0)

    def test_conflicting_existing_record_is_not_overwritten(self):
        destination = FakeDestination([{"kind": "login", "name": "SYNTHETIC"}], verified=False)
        self.assertEqual(destination.transfer(self.item)["status"], "conflict")
        self.assertEqual(destination.writes, 0)

    def test_case_conflict_is_not_overwritten(self):
        destination = FakeDestination([{"kind": "login", "name": "synthetic"}])
        self.assertEqual(destination.transfer(self.item)["status"], "conflict")
        self.assertEqual(destination.writes, 0)

    def test_lost_response_is_uncertain_without_retry(self):
        destination = FakeDestination(write_error=True)
        self.assertEqual(destination.transfer(self.item)["status"], "uncertain")
        self.assertEqual(destination.writes, 1)

    def test_failed_verification_is_not_success(self):
        destination = FakeDestination(verified=False)
        self.assertEqual(destination.transfer(self.item)["status"], "verification_failed")

    def test_stable_source_id_skips_renamed_reimport_and_blocks_changed_password(self):
        item = replace(self.item, name="First title [bw:00000000-0000-4000-8000-000000000001]",
                       source_name="First title", source_id="00000000-0000-4000-8000-000000000001")
        destination = FakeDestination([{"kind": "login", "name": item.name}])
        renamed = replace(item, name="New title · example.invalid [bw:00000000-0000-4000-8000-000000000001]",
                          source_name="New title")
        self.assertEqual(destination.transfer(renamed)["status"], "already_present")
        self.assertEqual(destination.writes, 0)
        destination.verified = False
        self.assertEqual(destination.transfer(renamed)["status"], "conflict")
        self.assertEqual(destination.writes, 0)

    def test_matching_legacy_entry_is_adopted_without_duplicate_write(self):
        item = replace(self.item, name="SYNTHETIC · example.invalid [bw:00000000-0000-4000-8000-000000000001]",
                       source_name="SYNTHETIC", source_id="00000000-0000-4000-8000-000000000001")
        destination = FakeDestination([{"kind": "login", "name": "SYNTHETIC"}])
        self.assertEqual(destination.transfer(item)["status"], "already_present")
        self.assertEqual(destination.writes, 0)


if __name__ == "__main__":
    unittest.main()
