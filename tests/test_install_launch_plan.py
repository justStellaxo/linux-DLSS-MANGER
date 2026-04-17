import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dlls_manager.launch_plan import build_install_launch_plan, list_installs_summary
from dlls_manager.override_db import save_install_override


class InstallLaunchPlanTests(unittest.TestCase):
    def test_build_install_launch_plan_for_steam_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            installs_file = Path(tmp) / "installs.json"
            overrides_dir = Path(tmp) / "overrides"
            payload = {
                "created_at": "2026-04-17T00:00:00Z",
                "warnings": [],
                "installs": [
                    {
                        "id": "steam:sample",
                        "display_name": "Sample Steam Game",
                        "source": "steam",
                        "source_id": "sample",
                        "launcher_family": "steam",
                        "store_family": "steam",
                        "execution_strategy": "steam_app",
                        "runtime": "proton-dx11",
                        "install_root": None,
                        "prefix_path": None,
                        "runner_name": None,
                        "runner_path": None,
                        "exe_path": None,
                        "script_path": None,
                        "desktop_file": None,
                        "app_id": "123456",
                        "launch_command": ["steam", "-applaunch", "123456"],
                        "launch_env": {},
                        "launch_args": "",
                        "wrapper_chain": [],
                        "working_directory": None,
                        "scan_paths": [],
                        "notes": [],
                        "validation_errors": [],
                        "validation_warnings": [],
                        "discovery_confidence": "high",
                        "anti_cheat": "none",
                        "anti_cheat_vendor": None,
                        "anti_cheat_policy": "verified_supported",
                        "supports_dlss_override": True,
                        "supports_dlss_version_selection": True,
                        "override_mode": "experimental",
                    }
                ],
            }
            installs_file.write_text(json.dumps(payload), encoding="utf-8")
            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir
            ):
                save_install_override(
                    "steam:sample",
                    {
                        "install_id": "steam:sample",
                        "extra_env": {},
                        "extra_wrappers": [],
                        "launch_args": "",
                        "dlss_version": None,
                        "enable_nvapi": None,
                        "enable_smooth_motion": None,
                        "use_gamemode": None,
                        "use_mangohud": None,
                        "allow_unsupported_override": None,
                        "sync_to_launcher": False,
                        "dlss_target_path": None,
                        "notes": [],
                    },
                )
                plan = build_install_launch_plan("steam:sample", "default")
                summary = list_installs_summary()

        self.assertEqual(plan["compatibility_status"], "ok")
        self.assertEqual(plan["release_support"]["level"], "supported")
        self.assertIn("steam -applaunch 123456", plan["command_preview"])
        self.assertEqual(summary[0]["id"], "steam:sample")
        self.assertEqual(summary[0]["release_support"], "supported")

    def test_steam_launch_plan_blocks_on_invalid_localconfig(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            steam_root = root / "Steam"
            localconfig = steam_root / "userdata" / "1000" / "config" / "localconfig.vdf"
            localconfig.parent.mkdir(parents=True)
            localconfig.write_text('"broken', encoding="utf-8")

            payload = {
                "created_at": "2026-04-17T00:00:00Z",
                "warnings": [],
                "installs": [
                    {
                        "id": "steam:sample",
                        "display_name": "Sample Steam Game",
                        "source": "steam",
                        "source_id": "sample",
                        "launcher_family": "steam",
                        "store_family": "steam",
                        "execution_strategy": "steam_app",
                        "runtime": "proton-dx11",
                        "install_root": None,
                        "prefix_path": None,
                        "runner_name": None,
                        "runner_path": None,
                        "exe_path": None,
                        "script_path": None,
                        "desktop_file": None,
                        "app_id": "123456",
                        "launch_command": ["steam", "-applaunch", "123456"],
                        "launch_env": {},
                        "launch_args": "",
                        "wrapper_chain": [],
                        "working_directory": None,
                        "scan_paths": [],
                        "notes": [],
                        "validation_errors": [],
                        "validation_warnings": [],
                        "discovery_confidence": "high",
                        "anti_cheat": "none",
                        "anti_cheat_vendor": None,
                        "anti_cheat_policy": "verified_supported",
                        "supports_dlss_override": True,
                        "supports_dlss_version_selection": True,
                        "override_mode": "experimental",
                    }
                ],
            }
            installs_file.write_text(json.dumps(payload), encoding="utf-8")
            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.launcher_persistence.STEAM_ROOT_DIRS", (steam_root,)
            ):
                plan = build_install_launch_plan("steam:sample", "default")

        self.assertEqual(plan["compatibility_status"], "blocked")
        self.assertTrue(any("Failed to prepare Steam localconfig sync" in reason for reason in plan["blocked_reasons"]))


if __name__ == "__main__":
    unittest.main()
