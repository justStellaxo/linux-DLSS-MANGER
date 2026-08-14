import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dlls_manager.override_db import load_install_override, update_install_override
from dlls_manager.profile_db import load_profile, save_profile, update_profile


class ProfileAndOverrideStoreTests(unittest.TestCase):
    def test_profile_update_persists_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profiles_dir = Path(tmp) / "profiles"
            profiles_dir.mkdir()
            with patch("dlls_manager.profile_db.PROFILES_DIR", profiles_dir):
                save_profile(
                    "custom",
                    {
                        "enable_nvapi": False,
                        "enable_smooth_motion": False,
                        "use_gamemode": False,
                        "use_mangohud": False,
                        "launch_args": "",
                        "custom_env": {},
                        "dlss_mode": "game_default",
                        "dlss_version": None,
                        "allow_unsupported_override": False,
                        "safety_mode": "strict",
                    },
                )
                updated = update_profile(
                    "custom",
                    {
                        "enable_nvapi": "true",
                        "custom_env.DXVK_HUD": "full",
                        "dlss_version": "3.7.10",
                    },
                )

        self.assertTrue(updated["enable_nvapi"])
        self.assertEqual(updated["custom_env"]["DXVK_HUD"], "full")
        self.assertEqual(updated["dlss_version"], "3.7.10")

    def test_install_override_update_persists_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            overrides_dir = Path(tmp) / "overrides"
            with patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir):
                updated = update_install_override(
                    "steam:sample-dx11",
                    {
                        "extra_env.DXVK_HUD": "1",
                        "extra_wrappers": "gamescope,mangohud",
                        "dlss_version": "2.5.1",
                        "sync_to_launcher": "false",
                    },
                )
                loaded = load_install_override("steam:sample-dx11")

        self.assertEqual(updated, loaded)
        self.assertEqual(loaded["extra_env"]["DXVK_HUD"], "1")
        self.assertEqual(loaded["extra_wrappers"], ["gamescope", "mangohud"])
        self.assertEqual(loaded["dlss_version"], "2.5.1")
        self.assertFalse(loaded["sync_to_launcher"])

    def test_install_override_defaults_launcher_sync_off(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            overrides_dir = Path(tmp) / "overrides"
            with patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir):
                loaded = load_install_override("steam:sample-dx11")

        self.assertFalse(loaded["sync_to_launcher"])


if __name__ == "__main__":
    unittest.main()
