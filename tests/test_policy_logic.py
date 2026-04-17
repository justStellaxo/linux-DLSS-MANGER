import unittest

from dlls_manager.anti_cheat import classify_game
from dlls_manager.game_db import get_game
from dlls_manager.launch_plan import build_launch_plan
from dlls_manager.profile_db import load_profile


class PolicyLogicTests(unittest.TestCase):
    def test_battleye_marker_detection(self) -> None:
        game = get_game("sample-vulkan")
        anti_cheat = classify_game(game)
        self.assertEqual(anti_cheat["vendor"], "BattlEye")
        self.assertEqual(anti_cheat["policy"], "blocked")

    def test_safe_profile_keeps_unknown_title_previewable(self) -> None:
        plan = build_launch_plan("sample-vulkan", "safe")
        self.assertEqual(plan["compatibility_status"], "ok")
        self.assertEqual(plan["command_preview"], "gamemoderun manual-launch sample-vulkan")

    def test_experimental_profile_blocks_battleye_title(self) -> None:
        plan = build_launch_plan("sample-vulkan", "experimental")
        self.assertEqual(plan["compatibility_status"], "blocked")

    def test_profile_loads_dlss_version(self) -> None:
        profile = load_profile("experimental")
        self.assertEqual(profile["dlss_version"], "3.7.10")


if __name__ == "__main__":
    unittest.main()
