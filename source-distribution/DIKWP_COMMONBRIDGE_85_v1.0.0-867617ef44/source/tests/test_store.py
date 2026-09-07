from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from commonbridge85.core import compile_capsule
from commonbridge85.store import WorkspaceStore


class StoreTests(unittest.TestCase):
    def test_put_get_counts_and_audit(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkspaceStore(Path(td) / "db.sqlite")
            c = compile_capsule({"title": "x", "problem": "y"})
            store.put("capsule", c, c["capsule_id"])
            self.assertEqual(store.get(c["capsule_id"])["capsule_id"], c["capsule_id"])
            self.assertEqual(store.counts()["capsule"], 1)
            self.assertTrue(store.verify_audit()["valid"])

    def test_reset(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkspaceStore(Path(td) / "db.sqlite")
            c = compile_capsule({"title": "x"})
            store.put("capsule", c, c["capsule_id"])
            store.reset()
            self.assertEqual(store.counts(), {})
            self.assertTrue(store.verify_audit()["valid"])


if __name__ == "__main__":
    unittest.main()
