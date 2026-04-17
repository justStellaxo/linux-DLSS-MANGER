import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dlls_manager.snapshots import build_snapshot_record, write_snapshot


class SnapshotTests(unittest.TestCase):
    def test_build_snapshot_record_wraps_payload(self) -> None:
        record = build_snapshot_record("preview", {"ok": True}, "2026-04-16T120000Z")
        self.assertEqual(record["command"], "preview")
        self.assertEqual(record["created_at"], "2026-04-16T120000Z")
        self.assertEqual(record["tool_version"], "0.2.0a1")
        self.assertEqual(record["summary"]["result_summary"], None)
        self.assertEqual(record["payload"], {"ok": True})

    def test_write_snapshot_persists_wrapped_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshots_dir = Path(tmp)
            with patch("dlls_manager.snapshots.SNAPSHOTS_DIR", snapshots_dir):
                path = Path(write_snapshot("policy", {"game_id": "sample-dx11"}))

            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["command"], "policy")
            self.assertEqual(payload["tool_version"], "0.2.0a1")
            self.assertEqual(payload["payload"]["game_id"], "sample-dx11")
            self.assertIn("created_at", payload)

    def test_snapshot_summary_extracts_install_context(self) -> None:
        record = build_snapshot_record(
            "prepare-launch",
            {
                "profile": "default",
                "compatibility_status": "warn",
                "release_support": {"level": "advanced", "note": "test"},
                "install": {"id": "faugus:battlenet"},
                "summary": {"warning_count": 2},
            },
            "2026-04-16T120000Z",
        )
        self.assertEqual(record["summary"]["install_id"], "faugus:battlenet")
        self.assertEqual(record["summary"]["profile"], "default")
        self.assertEqual(record["summary"]["compatibility_status"], "warn")
        self.assertEqual(record["summary"]["release_support"], "advanced")


if __name__ == "__main__":
    unittest.main()
