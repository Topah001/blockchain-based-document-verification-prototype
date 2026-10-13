import json
import unittest
from pathlib import Path

from document_ledger import Ledger, LedgerError


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(__file__).parent / "ledger-test-data.jsonl"
        self.path.unlink(missing_ok=True)
        self.addCleanup(self.path.unlink, missing_ok=True)
        self.ledger = Ledger(self.path)

    def test_records_only_hashes_and_links_entries(self):
        first = self.ledger.add_document(b"lesson content")
        second = self.ledger.add_document(b"another lesson")
        self.assertEqual(0, first.index)
        self.assertEqual(first.entry_hash, second.previous_hash)
        self.assertTrue(self.ledger.verify().valid)
        stored = self.path.read_text(encoding="utf-8")
        self.assertNotIn("lesson content", stored)
        self.assertNotIn("another lesson", stored)
        self.assertEqual(64, len(first.document_sha256))

    def test_document_content_can_be_verified(self):
        self.ledger.add_document(b"original")
        self.assertTrue(self.ledger.verify_document(0, b"original"))
        self.assertFalse(self.ledger.verify_document(0, b"changed"))
        self.assertFalse(self.ledger.verify_document(3, b"original"))

    def test_entry_mutation_is_detected(self):
        self.ledger.add_document(b"original")
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        raw["document_sha256"] = "a" * 64
        self.path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
        result = self.ledger.verify()
        self.assertFalse(result.valid)
        self.assertIn("entry hash", result.message)
        with self.assertRaises(LedgerError):
            self.ledger.add_document(b"new")

    def test_chain_link_mutation_is_detected(self):
        self.ledger.add_document(b"one")
        self.ledger.add_document(b"two")
        lines = self.path.read_text(encoding="utf-8").splitlines()
        second = json.loads(lines[1])
        second["previous_hash"] = "0" * 64
        lines[1] = json.dumps(second)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = self.ledger.verify()
        self.assertFalse(result.valid)
        self.assertIn("previous-hash link", result.message)

    def test_malformed_json_is_reported(self):
        self.path.write_text("{broken\n", encoding="utf-8")
        self.assertFalse(self.ledger.verify().valid)


if __name__ == "__main__":
    unittest.main()
