import unittest
from unittest.mock import patch

from dlls_manager.mock_data import build_mock_ui_script, export_mock_library


class MockUiDataTests(unittest.TestCase):
    def test_export_contains_capabilities_and_profiles(self) -> None:
        payload = export_mock_library()
        self.assertIn("capabilities", payload)
        self.assertTrue(payload["profiles"])
        self.assertEqual(payload["default_profile"], "default")
        self.assertIn("dlss_versions", payload)
        self.assertTrue(payload["dlss_versions"])
        self.assertIn("catalog_refresh", payload)

    def test_each_game_contains_all_profile_views(self) -> None:
        payload = export_mock_library()
        expected_profiles = set(payload["profiles"])
        self.assertTrue(payload["games"])

        for game in payload["games"]:
            self.assertEqual(set(game["profiles"]), expected_profiles)
            self.assertIn("release_support", game)
            self.assertIn("cli_commands", game)
            self.assertIn("prepare", game["cli_commands"])
            self.assertIn("apply", game["cli_commands"])
            self.assertIn("launch", game["cli_commands"])
            for profile_name, profile_view in game["profiles"].items():
                self.assertEqual(profile_view["launch_plan"]["profile"], profile_name)
                self.assertEqual(profile_view["policy_report"]["profile"], profile_name)
                self.assertIn("safety_mode", profile_view["profile_config"])
                self.assertIn("command_preview", profile_view["launch_plan"])
                self.assertIn("env", profile_view["launch_plan"])

    def test_script_bundle_wraps_payload_for_browser_loading(self) -> None:
        payload = export_mock_library()
        script = build_mock_ui_script(payload)
        self.assertTrue(script.startswith("window.MOCK_LIBRARY_DATA = "))
        self.assertIn('"games": [', script)

    def test_export_can_refresh_catalog_on_start(self) -> None:
        with patch("dlls_manager.mock_data.refresh_dlss_catalog", return_value={"latest_version": "310.5.3"}):
            payload = export_mock_library(refresh_catalog=True)
        self.assertEqual(payload["catalog_refresh"]["status"], "refreshed")
        self.assertEqual(payload["catalog_refresh"]["details"]["latest_version"], "310.5.3")


if __name__ == "__main__":
    unittest.main()
