import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dlls_manager.anti_cheat import load_rules
from dlls_manager.dlss_policy import load_dlss_versions
from dlls_manager.game_db import load_games
from dlls_manager.profile_db import load_profile


class DataValidationTests(unittest.TestCase):
    def test_games_json_rejects_non_string_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            games_path = Path(tmp) / "games.json"
            games_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "broken",
                            "name": "Broken",
                            "notes": ["valid", 3],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with patch("dlls_manager.game_db.GAMES_FILE", games_path):
                with self.assertRaisesRegex(ValueError, "notes as a list of strings"):
                    load_games()

    def test_profile_rejects_non_string_custom_env_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profiles_dir = Path(tmp)
            (profiles_dir / "broken.json").write_text(
                json.dumps({"custom_env": {"DXVK_HUD": 1}}),
                encoding="utf-8",
            )
            with patch("dlls_manager.profile_db.PROFILES_DIR", profiles_dir):
                with self.assertRaisesRegex(ValueError, "string-to-string object"):
                    load_profile("broken")

    def test_anti_cheat_rules_require_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_path = Path(tmp) / "anti_cheat_rules.json"
            rules_path.write_text(
                json.dumps([{"vendor": "BrokenVendor", "default_policy": "blocked"}]),
                encoding="utf-8",
            )
            with patch("dlls_manager.anti_cheat.ANTI_CHEAT_RULES_FILE", rules_path):
                with self.assertRaisesRegex(ValueError, "non-empty markers list"):
                    load_rules()

    def test_dlss_versions_require_boolean_selectable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            versions_path = Path(tmp) / "dlss_versions.json"
            versions_path.write_text(
                json.dumps([{"id": "3.7.10", "label": "DLSS 3.7.10", "selectable": "yes"}]),
                encoding="utf-8",
            )
            with patch("dlls_manager.dlss_catalog.DLSS_VERSIONS_FILE", versions_path):
                with self.assertRaisesRegex(ValueError, "selectable as a boolean"):
                    load_dlss_versions()


if __name__ == "__main__":
    unittest.main()
