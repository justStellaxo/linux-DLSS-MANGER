import unittest
from unittest.mock import patch

from dlls_manager.detector import detect_capabilities


class DetectorTests(unittest.TestCase):
    def test_detect_capabilities_reports_wrapper_tools(self) -> None:
        values = {
            "steam": "/usr/bin/steam",
            "mangohud": "/usr/bin/mangohud",
            "gamemoderun": "/usr/bin/gamemoderun",
            "gamescope": None,
            "mangoapp": None,
            "vulkaninfo": "/usr/bin/vulkaninfo",
            "nvidia-smi": "/usr/bin/nvidia-smi",
        }

        with patch("dlls_manager.detector.shutil.which", side_effect=lambda name: values.get(name)), patch(
            "dlls_manager.detector.run_cmd", return_value="ok"
        ):
            payload = detect_capabilities()

        self.assertTrue(payload["steam_available"])
        self.assertTrue(payload["mangohud_available"])
        self.assertTrue(payload["gamemode_available"])
        self.assertFalse(payload["gamescope_available"])
        self.assertFalse(payload["mangoapp_available"])


if __name__ == "__main__":
    unittest.main()
