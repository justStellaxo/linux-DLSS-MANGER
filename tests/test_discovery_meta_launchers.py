import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dlls_manager.discovery.bottles import discover_bottles_installations
from dlls_manager.discovery.heroic import discover_heroic_installations
from dlls_manager.discovery.lutris import discover_lutris_installations


class MetaLauncherDiscoveryTests(unittest.TestCase):
    def test_heroic_discovery_imports_installed_game_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "heroic"
            manifest_dir = root / "legendaryConfig" / "legendary"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "installed.json").write_text(
                json.dumps(
                    {
                        "Cyberpunk2077": {
                            "app_name": "Cyberpunk2077",
                            "title": "Cyberpunk 2077",
                            "install_path": "/games/Cyberpunk2077",
                            "winePrefix": "/prefixes/Cyberpunk2077",
                            "runner": "GE-Proton",
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.discovery.heroic.HEROIC_CONFIG_DIRS", (root,)):
                installs = discover_heroic_installations()

        self.assertEqual(len(installs), 1)
        install = installs[0]
        self.assertEqual(install["store_family"], "epic")
        self.assertEqual(install["execution_strategy"], "legendary_game")
        self.assertEqual(install["app_id"], "Cyberpunk2077")
        self.assertEqual(install["prefix_path"], "/prefixes/Cyberpunk2077")

    def test_heroic_discovery_skips_invalid_json_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "heroic"
            manifest_dir = root / "legendaryConfig" / "legendary"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "installed.json").write_text("{broken", encoding="utf-8")

            with patch("dlls_manager.discovery.heroic.HEROIC_CONFIG_DIRS", (root,)):
                installs = discover_heroic_installations()

        self.assertEqual(installs, [])

    def test_lutris_discovery_imports_game_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "lutris"
            games_dir = root / "games"
            games_dir.mkdir(parents=True)
            (games_dir / "cyberpunk-2077.yml").write_text(
                "\n".join(
                    [
                        "name: Cyberpunk 2077",
                        "game_slug: cyberpunk-2077",
                        "runner: wine",
                        "game:",
                        "  exe: /games/Cyberpunk2077/bin/x64/Cyberpunk2077.exe",
                        "  prefix: /prefixes/Cyberpunk2077",
                        "  working_dir: /games/Cyberpunk2077",
                    ]
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.discovery.lutris.LUTRIS_DIRS", (root,)):
                installs = discover_lutris_installations()

        self.assertEqual(len(installs), 1)
        install = installs[0]
        self.assertEqual(install["id"], "lutris:cyberpunk-2077")
        self.assertEqual(install["execution_strategy"], "lutris_game")
        self.assertEqual(install["prefix_path"], "/prefixes/Cyberpunk2077")
        self.assertEqual(install["launch_command"], ["lutris", "lutris:cyberpunk-2077"])

    def test_bottles_discovery_imports_programs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bottles"
            bottle_dir = root / "bottles" / "BattleNet"
            programs_dir = bottle_dir / "programs"
            programs_dir.mkdir(parents=True)
            (bottle_dir / "bottle.yml").write_text(
                "\n".join(
                    [
                        "Name: BattleNet",
                        "Runner: soda-9.0",
                    ]
                ),
                encoding="utf-8",
            )
            (programs_dir / "Battle.net.yml").write_text(
                "\n".join(
                    [
                        "name: Battle.net",
                        "path: /bottles/BattleNet/drive_c/Program Files (x86)/Battle.net/Battle.net.exe",
                    ]
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.discovery.bottles.BOTTLES_DIRS", (root,)):
                installs = discover_bottles_installations()

        self.assertEqual(len(installs), 1)
        install = installs[0]
        self.assertEqual(install["display_name"], "Battle.net")
        self.assertEqual(install["execution_strategy"], "bottles_program")
        self.assertIn("bottles-cli", install["launch_command"][0])
        self.assertEqual(install["runner_name"], "soda-9.0")

    def test_bottles_discovery_falls_back_to_bottle_when_no_program_entries_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bottles"
            bottle_dir = root / "bottles" / "FallbackBottle"
            bottle_dir.mkdir(parents=True)
            (bottle_dir / "bottle.yml").write_text(
                "\n".join(
                    [
                        "Name: FallbackBottle",
                        "Runner: soda-9.0",
                    ]
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.discovery.bottles.BOTTLES_DIRS", (root,)):
                installs = discover_bottles_installations()

        self.assertEqual(len(installs), 1)
        install = installs[0]
        self.assertEqual(install["display_name"], "FallbackBottle")
        self.assertEqual(install["discovery_confidence"], "low")


if __name__ == "__main__":
    unittest.main()
