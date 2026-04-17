import unittest

from dlls_manager.release_support import get_release_support


class ReleaseSupportTests(unittest.TestCase):
    def test_steam_is_supported(self) -> None:
        install = {
            "id": "steam:test",
            "display_name": "Test",
            "source": "steam",
            "source_id": "test",
            "launcher_family": "steam",
            "store_family": "steam",
            "execution_strategy": "steam_app",
            "runtime": "proton",
            "install_root": None,
            "prefix_path": None,
            "runner_name": None,
            "runner_path": None,
            "exe_path": None,
            "script_path": None,
            "desktop_file": None,
            "app_id": None,
            "launch_command": [],
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
            "supports_dlss_override": False,
            "supports_dlss_version_selection": False,
            "override_mode": "experimental",
        }

        support = get_release_support(install)

        self.assertEqual(support["level"], "supported")

    def test_heroic_is_experimental(self) -> None:
        install = {
            "id": "heroic:test",
            "display_name": "Test",
            "source": "heroic",
            "source_id": "test",
            "launcher_family": "heroic",
            "store_family": "epic",
            "execution_strategy": "heroic_game",
            "runtime": "proton",
            "install_root": None,
            "prefix_path": None,
            "runner_name": None,
            "runner_path": None,
            "exe_path": None,
            "script_path": None,
            "desktop_file": None,
            "app_id": None,
            "launch_command": [],
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
            "supports_dlss_override": False,
            "supports_dlss_version_selection": False,
            "override_mode": "experimental",
        }

        support = get_release_support(install)

        self.assertEqual(support["level"], "experimental")


if __name__ == "__main__":
    unittest.main()
