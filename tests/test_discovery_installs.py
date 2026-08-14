import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dlls_manager.discovery.desktop_entries import discover_desktop_entry_installations
from dlls_manager.discovery.faugus import discover_faugus_installations
from dlls_manager.discovery.starcitizen_lug import discover_starcitizen_lug_installations


class DiscoveryInstallTests(unittest.TestCase):
    def test_faugus_discovery_imports_prefix_and_wrappers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "faugus"
            config_dir.mkdir()
            prefix = root / "prefix"
            battle_dir = prefix / "drive_c" / "Program Files (x86)" / "Battle.net"
            battle_dir.mkdir(parents=True)
            exe_path = battle_dir / "Battle.net.exe"
            exe_path.write_text("", encoding="utf-8")
            (config_dir / "games.json").write_text(
                json.dumps(
                    [
                        {
                            "gameid": "battlenet",
                            "title": "Battle.net",
                            "path": str(exe_path),
                            "prefix": str(prefix),
                            "launch_arguments": "WINE_SIMULATE_WRITECOPY=1 PROTON_ENABLE_WAYLAND=0",
                            "runner": "Proton-GE Latest",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (config_dir / "envar.txt").write_text("MANGOHUD=1\n", encoding="utf-8")

            apps_dir = root / "applications"
            apps_dir.mkdir()
            (apps_dir / "battlenet.desktop").write_text(
                "\n".join(
                    [
                        "[Desktop Entry]",
                        "Name=Battle.net",
                        "Exec=/usr/bin/mullvad-exclude /usr/bin/faugus-run --game battlenet",
                    ]
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.discovery.faugus.FAUGUS_CONFIG_DIR", config_dir), patch(
                "dlls_manager.discovery.faugus.FAUGUS_GAMES_FILE", config_dir / "games.json"
            ), patch("dlls_manager.discovery.base.LOCAL_APPLICATIONS_DIR", apps_dir):
                installs = discover_faugus_installations()

        self.assertEqual(len(installs), 1)
        install = installs[0]
        self.assertEqual(install["id"], "faugus:battlenet")
        self.assertEqual(install["wrapper_chain"], ["mullvad-exclude"])
        self.assertEqual(install["launch_command"], ["/usr/bin/faugus-run", "--game", "battlenet"])
        self.assertEqual(install["launch_env"]["MANGOHUD"], "1")
        self.assertEqual(install["launch_env"]["WINE_SIMULATE_WRITECOPY"], "1")

    def test_starcitizen_lug_discovery_imports_script_and_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lug_dir = root / "starcitizen-lug"
            lug_dir.mkdir()
            prefix = root / "star-citizen"
            (prefix / "drive_c" / "Program Files" / "Roberts Space Industries" / "RSI Launcher").mkdir(parents=True)
            (prefix / "drive_c" / "Program Files" / "Roberts Space Industries" / "RSI Launcher" / "RSI Launcher.exe").write_text(
                "",
                encoding="utf-8",
            )
            script_path = prefix / "sc-launch.sh"
            script_path.write_text(
                "\n".join(
                    [
                        '#!/usr/bin/env bash',
                        '# export wine_path="/path/to/custom/runner/bin"',
                        f'export WINEPREFIX="{prefix}"',
                        f'export wine_path="{prefix}/runners/lug-wine/bin"',
                    ]
                ),
                encoding="utf-8",
            )
            (lug_dir / "gamedir.conf").write_text(str(prefix / "drive_c" / "Program Files" / "Roberts Space Industries" / "StarCitizen"), encoding="utf-8")
            (lug_dir / "winedir.conf").write_text(str(prefix), encoding="utf-8")

            apps_dir = root / "applications"
            apps_dir.mkdir()
            (apps_dir / "rsi launcher.exe.desktop").write_text(
                "\n".join(
                    [
                        "[Desktop Entry]",
                        "Name=RSI Launcher",
                        f'Exec=/usr/bin/mullvad-exclude "{script_path}"',
                    ]
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.discovery.starcitizen_lug.STARCITIZEN_LUG_DIR", lug_dir), patch(
                "dlls_manager.discovery.base.LOCAL_APPLICATIONS_DIR", apps_dir
            ):
                installs = discover_starcitizen_lug_installations()

        self.assertEqual(len(installs), 1)
        install = installs[0]
        self.assertEqual(install["execution_strategy"], "script_exec")
        self.assertEqual(install["wrapper_chain"], ["mullvad-exclude"])
        self.assertEqual(install["script_path"], str(script_path))
        self.assertEqual(install["runner_path"], f"{prefix}/runners/lug-wine/bin")
        self.assertEqual(install["runner_name"], "lug-wine")
        self.assertTrue(str(install["exe_path"]).endswith("RSI Launcher.exe"))

    def test_desktop_entry_discovery_classifies_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            apps_dir = Path(tmp) / "applications"
            apps_dir.mkdir()
            script_path = Path(tmp) / "run-game.sh"
            script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (apps_dir / "game.desktop").write_text(
                "\n".join(
                    [
                        "[Desktop Entry]",
                        "Name=Custom Game",
                        f"Exec={script_path}",
                    ]
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.discovery.base.LOCAL_APPLICATIONS_DIR", apps_dir):
                installs = discover_desktop_entry_installations()

        self.assertEqual(len(installs), 1)
        self.assertEqual(installs[0]["execution_strategy"], "script_exec")

    def test_desktop_entry_discovery_skips_non_game_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            apps_dir = Path(tmp) / "applications"
            apps_dir.mkdir()
            binary_path = Path(tmp) / "jetbrains-toolbox"
            binary_path.write_text("", encoding="utf-8")
            (apps_dir / "toolbox.desktop").write_text(
                "\n".join(
                    [
                        "[Desktop Entry]",
                        "Name=JetBrains Toolbox",
                        f"Exec={binary_path}",
                        "Categories=Development;IDE;",
                    ]
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.discovery.base.LOCAL_APPLICATIONS_DIR", apps_dir):
                installs = discover_desktop_entry_installations()

        self.assertEqual(installs, [])

    def test_desktop_entry_discovery_promotes_steam_uri_entries_to_steam_shortcuts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            apps_dir = Path(tmp) / "applications"
            apps_dir.mkdir()
            (apps_dir / "warhammer3.desktop").write_text(
                "\n".join(
                    [
                        "[Desktop Entry]",
                        "Name=Total War: WARHAMMER III",
                        "Categories=Game;",
                        "Exec=/usr/bin/gamemoderun /usr/bin/steam steam://rungameid/1142710",
                    ]
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.discovery.base.LOCAL_APPLICATIONS_DIR", apps_dir):
                installs = discover_desktop_entry_installations()

        self.assertEqual(len(installs), 1)
        install = installs[0]
        self.assertEqual(install["launcher_family"], "steam")
        self.assertEqual(install["store_family"], "steam")
        self.assertEqual(install["execution_strategy"], "steam_shortcut")
        self.assertEqual(install["app_id"], "1142710")
        self.assertEqual(install["launch_command"], ["steam", "-applaunch", "1142710"])
        self.assertEqual(install["wrapper_chain"], ["gamemoderun"])
        self.assertIsNone(install["install_root"])
        self.assertIsNone(install["exe_path"])
        self.assertEqual(install["scan_paths"], [])
        self.assertIn("Steam shortcut", install["notes"][0])


if __name__ == "__main__":
    unittest.main()
