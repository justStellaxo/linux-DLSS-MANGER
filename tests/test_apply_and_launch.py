import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dlls_manager.launcher_runtime import apply_install_plan, launch_install, prepare_launch
from dlls_manager.mutations import apply_mutation_plan, load_rollback_record, rollback_mutation
from dlls_manager.override_db import save_install_override
from dlls_manager.profile_db import save_profile


class ApplyAndLaunchTests(unittest.TestCase):
    @staticmethod
    def _empty_override(install_id: str) -> dict:
        return {
            "install_id": install_id,
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
        }

    def test_apply_updates_steam_localconfig_and_rollback_restores_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            steam_root = root / "Steam"
            localconfig = steam_root / "userdata" / "1000" / "config" / "localconfig.vdf"
            localconfig.parent.mkdir(parents=True)
            original_localconfig = "\n".join(
                [
                    '"UserLocalConfigStore"',
                    "{",
                    '\t"Software"',
                    "\t{",
                    '\t\t"Valve"',
                    "\t\t{",
                    '\t\t\t"Steam"',
                    "\t\t\t{",
                    '\t\t\t\t"apps"',
                    "\t\t\t\t{",
                    '\t\t\t\t\t"999999"',
                    "\t\t\t\t\t{",
                    '\t\t\t\t\t\t"LaunchOptions"\t\t"--keep"',
                    "\t\t\t\t\t}",
                    '\t\t\t\t\t"123456"',
                    "\t\t\t\t\t{",
                    '\t\t\t\t\t\t"LastPlayed"\t\t"0"',
                    "\t\t\t\t\t}",
                    "\t\t\t\t}",
                    "\t\t\t}",
                    "\t\t}",
                    "\t}",
                    "}",
                    "",
                ]
            )
            localconfig.write_text(original_localconfig, encoding="utf-8")
            profiles_dir.mkdir()

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-17T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "steam:test-game",
                                "display_name": "Steam Test Game",
                                "source": "steam",
                                "source_id": "test-game",
                                "launcher_family": "steam",
                                "store_family": "steam",
                                "execution_strategy": "steam_app",
                                "runtime": "proton-dx11",
                                "install_root": str(root / "game"),
                                "prefix_path": None,
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": None,
                                "desktop_file": None,
                                "app_id": "123456",
                                "launch_command": ["steam", "-applaunch", "123456"],
                                "launch_env": {},
                                "launch_args": "--from-install",
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
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ), patch("dlls_manager.launcher_persistence.STEAM_ROOT_DIRS", (steam_root,)):
                save_profile(
                    "default",
                    {
                        "enable_nvapi": True,
                        "enable_smooth_motion": False,
                        "use_gamemode": True,
                        "use_mangohud": False,
                        "launch_args": "--from-profile",
                        "custom_env": {"DXVK_HUD": "0"},
                        "dlss_mode": "game_default",
                        "dlss_version": None,
                        "allow_unsupported_override": False,
                        "safety_mode": "strict",
                    },
                )
                save_install_override(
                    "steam:test-game",
                    {
                        **self._empty_override("steam:test-game"),
                        "sync_to_launcher": True,
                    },
                )

                prepared = prepare_launch("steam:test-game", "default")
                self.assertEqual(prepared["launch_plan"]["args"], "--from-install --from-profile")
                self.assertTrue(
                    any(step["target_path"] == str(localconfig) for step in prepared["mutation_plan"]["steps"]),
                    prepared["mutation_plan"]["steps"],
                )

                applied = apply_install_plan("steam:test-game", "default")
                self.assertTrue(applied["ok"], applied["errors"])

                updated = localconfig.read_text(encoding="utf-8")
                self.assertIn('"999999"', updated)
                self.assertIn(
                    '"LaunchOptions"\t\t"DXVK_ENABLE_NVAPI=1 DXVK_HUD=0 PROTON_ENABLE_NVAPI=1 gamemoderun %command% --from-install --from-profile"',
                    updated,
                )

                rollback = rollback_mutation(str(applied["rollback_id"]))
                self.assertTrue(rollback["ok"], rollback["errors"])
                self.assertEqual(localconfig.read_text(encoding="utf-8"), original_localconfig)

    def test_apply_updates_steam_localconfig_for_desktop_steam_shortcut_installs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            steam_root = root / "Steam"
            localconfig = steam_root / "userdata" / "1000" / "config" / "localconfig.vdf"
            localconfig.parent.mkdir(parents=True)
            localconfig.write_text(
                "\n".join(
                    [
                        '"UserLocalConfigStore"',
                        "{",
                        '\t"Software"',
                        "\t{",
                        '\t\t"Valve"',
                        "\t\t{",
                        '\t\t\t"Steam"',
                        "\t\t\t{",
                        '\t\t\t\t"apps"',
                        "\t\t\t\t{",
                        '\t\t\t\t\t"1142710"',
                        "\t\t\t\t\t{",
                        '\t\t\t\t\t\t"LastPlayed"\t\t"0"',
                        "\t\t\t\t\t}",
                        "\t\t\t\t}",
                        "\t\t\t}",
                        "\t\t}",
                        "\t}",
                        "}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            profiles_dir.mkdir()

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-17T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "desktop_entry:warhammer3",
                                "display_name": "Total War: WARHAMMER III",
                                "source": "desktop_entry",
                                "source_id": "warhammer3",
                                "launcher_family": "steam",
                                "store_family": "steam",
                                "execution_strategy": "steam_shortcut",
                                "runtime": "steam",
                                "install_root": None,
                                "prefix_path": None,
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": None,
                                "desktop_file": str(root / "warhammer3.desktop"),
                                "app_id": "1142710",
                                "launch_command": ["steam", "-applaunch", "1142710"],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": ["mullvad-exclude"],
                                "working_directory": None,
                                "scan_paths": [],
                                "notes": ["Imported from desktop entry discovery as a Steam shortcut."],
                                "validation_errors": [],
                                "validation_warnings": [],
                                "discovery_confidence": "medium",
                                "anti_cheat": "unknown",
                                "anti_cheat_vendor": None,
                                "anti_cheat_policy": "warn",
                                "supports_dlss_override": False,
                                "supports_dlss_version_selection": False,
                                "override_mode": "experimental",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ), patch("dlls_manager.launcher_persistence.STEAM_ROOT_DIRS", (steam_root,)):
                save_profile(
                    "default",
                    {
                        "enable_nvapi": False,
                        "enable_smooth_motion": False,
                        "use_gamemode": True,
                        "use_mangohud": True,
                        "launch_args": "",
                        "custom_env": {"DXVK_HUD": "0"},
                        "dlss_mode": "game_default",
                        "dlss_version": None,
                        "allow_unsupported_override": False,
                        "safety_mode": "strict",
                    },
                )
                save_install_override(
                    "desktop_entry:warhammer3",
                    {
                        **self._empty_override("desktop_entry:warhammer3"),
                        "sync_to_launcher": True,
                    },
                )

                prepared = prepare_launch("desktop_entry:warhammer3", "default")
                self.assertEqual(prepared["execution"]["executable"], ["steam", "-applaunch", "1142710"])
                self.assertTrue(
                    any(step["target_path"] == str(localconfig) for step in prepared["mutation_plan"]["steps"]),
                    prepared["mutation_plan"]["steps"],
                )

                applied = apply_install_plan("desktop_entry:warhammer3", "default")
                self.assertTrue(applied["ok"], applied["errors"])

                updated = localconfig.read_text(encoding="utf-8")
                self.assertIn(
                    '"LaunchOptions"\t\t"DXVK_HUD=0 gamemoderun mangohud mullvad-exclude %command%"',
                    updated,
                )

    def test_apply_creates_backup_and_rollback_restores_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            dlss_runtime_dir = root / "dlss_runtime"
            lug_dir = root / "lug"
            install_root = root / "game"
            install_root.mkdir(parents=True)
            profiles_dir.mkdir()
            lug_dir.mkdir()
            target_dll = install_root / "nvngx_dlss.dll"
            target_dll.write_text("old-runtime", encoding="utf-8")
            runtime_dir = dlss_runtime_dir / "3.7.10"
            runtime_dir.mkdir(parents=True)
            (runtime_dir / "nvngx_dlss.dll").write_text("new-runtime", encoding="utf-8")
            marker_path = root / "launched.txt"

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-17T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "starcitizen_lug:test-game",
                                "display_name": "Test Game",
                                "source": "starcitizen_lug",
                                "source_id": "test-game",
                                "launcher_family": "rsi",
                                "store_family": "rsi",
                                "execution_strategy": "native_exec",
                                "runtime": "native",
                                "install_root": str(install_root),
                                "prefix_path": str(install_root),
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": None,
                                "desktop_file": None,
                                "app_id": None,
                                "launch_command": [
                                    sys.executable,
                                    "-c",
                                    f"from pathlib import Path; Path(r'{marker_path}').write_text('ok', encoding='utf-8')",
                                ],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": [],
                                "working_directory": str(root),
                                "scan_paths": [str(install_root)],
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
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ), patch("dlls_manager.dlss_mutations.DLSS_RUNTIME_DIR", dlss_runtime_dir), patch(
                "dlls_manager.launcher_persistence.STARCITIZEN_LUG_DIR", lug_dir
            ):
                save_profile(
                    "default",
                    {
                        "enable_nvapi": False,
                        "enable_smooth_motion": False,
                        "use_gamemode": False,
                        "use_mangohud": False,
                        "launch_args": "",
                        "custom_env": {},
                        "dlss_mode": "game_default",
                        "dlss_version": "3.7.10",
                        "allow_unsupported_override": False,
                        "safety_mode": "strict",
                    },
                )
                save_install_override(
                    "starcitizen_lug:test-game",
                    {
                        "install_id": "starcitizen_lug:test-game",
                        "extra_env": {"DXVK_HUD": "1"},
                        "extra_wrappers": [],
                        "launch_args": "",
                        "dlss_version": None,
                        "enable_nvapi": None,
                        "enable_smooth_motion": None,
                        "use_gamemode": None,
                        "use_mangohud": None,
                        "allow_unsupported_override": None,
                        "sync_to_launcher": True,
                        "dlss_target_path": str(target_dll),
                        "notes": ["test"],
                    },
                )
                prepared = prepare_launch("starcitizen_lug:test-game", "default")
                self.assertEqual(len(prepared["mutation_plan"]["steps"]), 2)

                applied = apply_install_plan("starcitizen_lug:test-game", "default")
                self.assertTrue(applied["ok"], applied["errors"])
                self.assertEqual(target_dll.read_text(encoding="utf-8"), "new-runtime")
                rollback_id = str(applied["rollback_id"])
                record = load_rollback_record(rollback_id)
                self.assertEqual(record["install_id"], "starcitizen_lug:test-game")
                sidecar = lug_dir / "dlls_manager_overrides" / "test-game.json"
                self.assertTrue(sidecar.exists())

                rollback = rollback_mutation(rollback_id)
                self.assertTrue(rollback["ok"], rollback["errors"])
                self.assertEqual(target_dll.read_text(encoding="utf-8"), "old-runtime")

    def test_launch_wait_executes_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            install_root = root / "game"
            install_root.mkdir(parents=True)
            marker_path = root / "launched.txt"

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-17T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "manual:test-launch",
                                "display_name": "Launch Test",
                                "source": "manual",
                                "source_id": "test-launch",
                                "launcher_family": "manual",
                                "store_family": "generic",
                                "execution_strategy": "native_exec",
                                "runtime": "native",
                                "install_root": str(install_root),
                                "prefix_path": None,
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": None,
                                "desktop_file": None,
                                "app_id": None,
                                "launch_command": [
                                    sys.executable,
                                    "-c",
                                    f"from pathlib import Path; Path(r'{marker_path}').write_text('ok', encoding='utf-8')",
                                ],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": [],
                                "working_directory": str(root),
                                "scan_paths": [str(install_root)],
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
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ):
                save_profile(
                    "default",
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
                result = launch_install("manual:test-launch", "default", wait=True)
                self.assertTrue(result["ok"], result["errors"])
                self.assertEqual(marker_path.read_text(encoding="utf-8"), "ok")

    def test_apply_failure_auto_rolls_back_partial_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rollbacks_dir = root / "rollbacks"
            source_ok = root / "source-ok.dll"
            source_ok.write_text("new-runtime", encoding="utf-8")
            target_ok = root / "target-ok.dll"
            target_ok.write_text("old-runtime", encoding="utf-8")

            plan = {
                "install_id": "manual:test-partial-failure",
                "profile": "default",
                "override": self._empty_override("manual:test-partial-failure"),
                "created_at": "2026-04-17T00:00:00Z",
                "status": "ok",
                "steps": [
                    {
                        "id": "copy-ok",
                        "action": "copy_file",
                        "description": "Write the first file successfully.",
                        "source_path": str(source_ok),
                        "target_path": str(target_ok),
                        "payload": None,
                        "backup_required": True,
                    },
                    {
                        "id": "copy-missing",
                        "action": "copy_file",
                        "description": "Fail on the second file.",
                        "source_path": str(root / "missing.dll"),
                        "target_path": str(root / "target-missing.dll"),
                        "payload": None,
                        "backup_required": True,
                    },
                ],
                "warnings": [],
                "blocked_reasons": [],
                "compatibility_status": "ok",
            }

            with patch("dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir):
                result = apply_mutation_plan(plan)
                self.assertFalse(result["ok"])
                self.assertEqual(target_ok.read_text(encoding="utf-8"), "old-runtime")
                self.assertTrue(any("automatic rollback restored" in warning.lower() for warning in result["warnings"]))
                rollback_id = str(result["rollback_id"])
                record = load_rollback_record(rollback_id)
                self.assertEqual(record["metadata"]["status"], "failed_rolled_back")
                self.assertTrue(record["metadata"]["auto_rollback"]["attempted"])
                self.assertEqual(record["metadata"]["auto_rollback"]["errors"], [])

    def test_launch_dry_run_does_not_mutate_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            dlss_runtime_dir = root / "dlss_runtime"
            lug_dir = root / "lug"
            install_root = root / "game"
            install_root.mkdir(parents=True)
            profiles_dir.mkdir()
            lug_dir.mkdir()
            target_dll = install_root / "nvngx_dlss.dll"
            target_dll.write_text("old-runtime", encoding="utf-8")
            runtime_dir = dlss_runtime_dir / "3.7.10"
            runtime_dir.mkdir(parents=True)
            (runtime_dir / "nvngx_dlss.dll").write_text("new-runtime", encoding="utf-8")

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-17T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "starcitizen_lug:test-dry-run",
                                "display_name": "Dry Run Test",
                                "source": "starcitizen_lug",
                                "source_id": "test-dry-run",
                                "launcher_family": "rsi",
                                "store_family": "rsi",
                                "execution_strategy": "native_exec",
                                "runtime": "native",
                                "install_root": str(install_root),
                                "prefix_path": str(install_root),
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": None,
                                "desktop_file": None,
                                "app_id": None,
                                "launch_command": [sys.executable, "-c", "print('dry-run')"],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": [],
                                "working_directory": str(root),
                                "scan_paths": [str(install_root)],
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
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ), patch("dlls_manager.dlss_mutations.DLSS_RUNTIME_DIR", dlss_runtime_dir), patch(
                "dlls_manager.launcher_persistence.STARCITIZEN_LUG_DIR", lug_dir
            ):
                save_profile(
                    "default",
                    {
                        "enable_nvapi": False,
                        "enable_smooth_motion": False,
                        "use_gamemode": False,
                        "use_mangohud": False,
                        "launch_args": "",
                        "custom_env": {},
                        "dlss_mode": "game_default",
                        "dlss_version": "3.7.10",
                        "allow_unsupported_override": False,
                        "safety_mode": "strict",
                    },
                )
                save_install_override(
                    "starcitizen_lug:test-dry-run",
                    {
                        "install_id": "starcitizen_lug:test-dry-run",
                        "extra_env": {},
                        "extra_wrappers": [],
                        "launch_args": "",
                        "dlss_version": None,
                        "enable_nvapi": None,
                        "enable_smooth_motion": None,
                        "use_gamemode": None,
                        "use_mangohud": None,
                        "allow_unsupported_override": None,
                        "sync_to_launcher": True,
                        "dlss_target_path": str(target_dll),
                        "notes": [],
                    },
                )

                result = launch_install("starcitizen_lug:test-dry-run", "default", dry_run=True)
                self.assertTrue(result["ok"], result["errors"])
                self.assertEqual(target_dll.read_text(encoding="utf-8"), "old-runtime")
                self.assertFalse((lug_dir / "dlls_manager_overrides" / "test-dry-run.json").exists())
                self.assertFalse(rollbacks_dir.exists())

    def test_launch_start_failure_auto_rolls_back_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            dlss_runtime_dir = root / "dlss_runtime"
            lug_dir = root / "lug"
            install_root = root / "game"
            install_root.mkdir(parents=True)
            profiles_dir.mkdir()
            lug_dir.mkdir()
            target_dll = install_root / "nvngx_dlss.dll"
            target_dll.write_text("old-runtime", encoding="utf-8")
            runtime_dir = dlss_runtime_dir / "3.7.10"
            runtime_dir.mkdir(parents=True)
            (runtime_dir / "nvngx_dlss.dll").write_text("new-runtime", encoding="utf-8")

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-17T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "starcitizen_lug:test-launch-failure",
                                "display_name": "Launch Failure Test",
                                "source": "starcitizen_lug",
                                "source_id": "test-launch-failure",
                                "launcher_family": "rsi",
                                "store_family": "rsi",
                                "execution_strategy": "native_exec",
                                "runtime": "native",
                                "install_root": str(install_root),
                                "prefix_path": str(install_root),
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": None,
                                "desktop_file": None,
                                "app_id": None,
                                "launch_command": ["/definitely/missing/binary"],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": [],
                                "working_directory": str(root),
                                "scan_paths": [str(install_root)],
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
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ), patch("dlls_manager.dlss_mutations.DLSS_RUNTIME_DIR", dlss_runtime_dir), patch(
                "dlls_manager.launcher_persistence.STARCITIZEN_LUG_DIR", lug_dir
            ), patch(
                "dlls_manager.launcher_runtime.subprocess.Popen", side_effect=FileNotFoundError("boom")
            ):
                save_profile(
                    "default",
                    {
                        "enable_nvapi": False,
                        "enable_smooth_motion": False,
                        "use_gamemode": False,
                        "use_mangohud": False,
                        "launch_args": "",
                        "custom_env": {},
                        "dlss_mode": "game_default",
                        "dlss_version": "3.7.10",
                        "allow_unsupported_override": False,
                        "safety_mode": "strict",
                    },
                )
                save_install_override(
                    "starcitizen_lug:test-launch-failure",
                    {
                        "install_id": "starcitizen_lug:test-launch-failure",
                        "extra_env": {},
                        "extra_wrappers": [],
                        "launch_args": "",
                        "dlss_version": None,
                        "enable_nvapi": None,
                        "enable_smooth_motion": None,
                        "use_gamemode": None,
                        "use_mangohud": None,
                        "allow_unsupported_override": None,
                        "sync_to_launcher": True,
                        "dlss_target_path": str(target_dll),
                        "notes": [],
                    },
                )

                result = launch_install("starcitizen_lug:test-launch-failure", "default")
                self.assertFalse(result["ok"])
                self.assertEqual(target_dll.read_text(encoding="utf-8"), "old-runtime")
                self.assertFalse((lug_dir / "dlls_manager_overrides" / "test-launch-failure.json").exists())
                self.assertTrue(any("automatic rollback restored" in warning.lower() for warning in result["warnings"]))

    def test_launch_wait_nonzero_exit_auto_rolls_back_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            dlss_runtime_dir = root / "dlss_runtime"
            lug_dir = root / "lug"
            install_root = root / "game"
            install_root.mkdir(parents=True)
            profiles_dir.mkdir()
            lug_dir.mkdir()
            target_dll = install_root / "nvngx_dlss.dll"
            target_dll.write_text("old-runtime", encoding="utf-8")
            runtime_dir = dlss_runtime_dir / "3.7.10"
            runtime_dir.mkdir(parents=True)
            (runtime_dir / "nvngx_dlss.dll").write_text("new-runtime", encoding="utf-8")

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-17T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "starcitizen_lug:test-wait-exit-failure",
                                "display_name": "Wait Exit Failure Test",
                                "source": "starcitizen_lug",
                                "source_id": "test-wait-exit-failure",
                                "launcher_family": "rsi",
                                "store_family": "rsi",
                                "execution_strategy": "native_exec",
                                "runtime": "native",
                                "install_root": str(install_root),
                                "prefix_path": str(install_root),
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": None,
                                "desktop_file": None,
                                "app_id": None,
                                "launch_command": [sys.executable, "-c", "import sys; sys.exit(23)"],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": [],
                                "working_directory": str(root),
                                "scan_paths": [str(install_root)],
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
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ), patch("dlls_manager.dlss_mutations.DLSS_RUNTIME_DIR", dlss_runtime_dir), patch(
                "dlls_manager.launcher_persistence.STARCITIZEN_LUG_DIR", lug_dir
            ):
                save_profile(
                    "default",
                    {
                        "enable_nvapi": False,
                        "enable_smooth_motion": False,
                        "use_gamemode": False,
                        "use_mangohud": False,
                        "launch_args": "",
                        "custom_env": {},
                        "dlss_mode": "game_default",
                        "dlss_version": "3.7.10",
                        "allow_unsupported_override": False,
                        "safety_mode": "strict",
                    },
                )
                save_install_override(
                    "starcitizen_lug:test-wait-exit-failure",
                    {
                        "install_id": "starcitizen_lug:test-wait-exit-failure",
                        "extra_env": {},
                        "extra_wrappers": [],
                        "launch_args": "",
                        "dlss_version": None,
                        "enable_nvapi": None,
                        "enable_smooth_motion": None,
                        "use_gamemode": None,
                        "use_mangohud": None,
                        "allow_unsupported_override": None,
                        "sync_to_launcher": True,
                        "dlss_target_path": str(target_dll),
                        "notes": [],
                    },
                )

                result = launch_install("starcitizen_lug:test-wait-exit-failure", "default", wait=True)
                self.assertFalse(result["ok"])
                self.assertEqual(result["returncode"], 23)
                self.assertEqual(result["errors"], ["Launch exited with status 23"])
                self.assertEqual(target_dll.read_text(encoding="utf-8"), "old-runtime")
                self.assertFalse((lug_dir / "dlls_manager_overrides" / "test-wait-exit-failure.json").exists())
                self.assertTrue(any("automatic rollback restored" in warning.lower() for warning in result["warnings"]))

    def test_launch_wait_nonzero_exit_records_applied_steps_in_rollback_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            dlss_runtime_dir = root / "dlss_runtime"
            lug_dir = root / "lug"
            install_root = root / "game"
            install_root.mkdir(parents=True)
            profiles_dir.mkdir()
            lug_dir.mkdir()
            target_dll = install_root / "nvngx_dlss.dll"
            target_dll.write_text("old-runtime", encoding="utf-8")
            runtime_dir = dlss_runtime_dir / "3.7.10"
            runtime_dir.mkdir(parents=True)
            (runtime_dir / "nvngx_dlss.dll").write_text("new-runtime", encoding="utf-8")

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-17T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "starcitizen_lug:test-wait-exit-manifest",
                                "display_name": "Wait Exit Manifest Test",
                                "source": "starcitizen_lug",
                                "source_id": "test-wait-exit-manifest",
                                "launcher_family": "rsi",
                                "store_family": "rsi",
                                "execution_strategy": "native_exec",
                                "runtime": "native",
                                "install_root": str(install_root),
                                "prefix_path": str(install_root),
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": None,
                                "desktop_file": None,
                                "app_id": None,
                                "launch_command": [sys.executable, "-c", "import sys; sys.exit(17)"],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": [],
                                "working_directory": str(root),
                                "scan_paths": [str(install_root)],
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
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ), patch("dlls_manager.dlss_mutations.DLSS_RUNTIME_DIR", dlss_runtime_dir), patch(
                "dlls_manager.launcher_persistence.STARCITIZEN_LUG_DIR", lug_dir
            ):
                save_profile(
                    "default",
                    {
                        "enable_nvapi": False,
                        "enable_smooth_motion": False,
                        "use_gamemode": False,
                        "use_mangohud": False,
                        "launch_args": "",
                        "custom_env": {},
                        "dlss_mode": "game_default",
                        "dlss_version": "3.7.10",
                        "allow_unsupported_override": False,
                        "safety_mode": "strict",
                    },
                )
                save_install_override(
                    "starcitizen_lug:test-wait-exit-manifest",
                    {
                        "install_id": "starcitizen_lug:test-wait-exit-manifest",
                        "extra_env": {},
                        "extra_wrappers": [],
                        "launch_args": "",
                        "dlss_version": None,
                        "enable_nvapi": None,
                        "enable_smooth_motion": None,
                        "use_gamemode": None,
                        "use_mangohud": None,
                        "allow_unsupported_override": None,
                        "sync_to_launcher": True,
                        "dlss_target_path": str(target_dll),
                        "notes": [],
                    },
                )

                result = launch_install("starcitizen_lug:test-wait-exit-manifest", "default", wait=True)
                self.assertFalse(result["ok"])
                self.assertIsNotNone(result["applied"])

                rollback_id = str(result["applied"]["rollback_id"])
                record = load_rollback_record(rollback_id)
                self.assertEqual(record["install_id"], "starcitizen_lug:test-wait-exit-manifest")
                self.assertEqual(
                    record["metadata"]["applied_steps"],
                    [
                        "dlss-3.7.10",
                        "sync-rsi-starcitizen_lug:test-wait-exit-manifest",
                    ],
                )
                self.assertEqual(len(record["files"]), 2)
                self.assertEqual(
                    {entry["target_path"] for entry in record["files"]},
                    {
                        str(target_dll),
                        str(lug_dir / "dlls_manager_overrides" / "test-wait-exit-manifest.json"),
                    },
                )

    def test_launch_skips_automatic_steam_start_when_sync_is_active_and_steam_is_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            steam_root = root / "Steam"
            localconfig = steam_root / "userdata" / "1000" / "config" / "localconfig.vdf"
            localconfig.parent.mkdir(parents=True)
            localconfig.write_text(
                "\n".join(
                    [
                        '"UserLocalConfigStore"',
                        "{",
                        '\t"Software"',
                        "\t{",
                        '\t\t"Valve"',
                        "\t\t{",
                        '\t\t\t"Steam"',
                        "\t\t\t{",
                        '\t\t\t\t"apps"',
                        "\t\t\t\t{",
                        '\t\t\t\t\t"123456"',
                        "\t\t\t\t\t{",
                        '\t\t\t\t\t\t"LastPlayed"\t\t"0"',
                        "\t\t\t\t\t}",
                        "\t\t\t\t}",
                        "\t\t\t}",
                        "\t\t}",
                        "\t}",
                        "}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            profiles_dir.mkdir()
            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-17T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "steam:test-running",
                                "display_name": "Steam Running Test",
                                "source": "steam",
                                "source_id": "test-running",
                                "launcher_family": "steam",
                                "store_family": "steam",
                                "execution_strategy": "steam_app",
                                "runtime": "proton-dx11",
                                "install_root": str(root / "game"),
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
                ),
                encoding="utf-8",
            )

            with patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ), patch("dlls_manager.launcher_persistence.STEAM_ROOT_DIRS", (steam_root,)), patch(
                "dlls_manager.launcher_runtime._steam_is_running", return_value=True
            ), patch("dlls_manager.launcher_runtime.subprocess.Popen") as popen_mock:
                save_profile(
                    "default",
                    {
                        "enable_nvapi": True,
                        "enable_smooth_motion": False,
                        "use_gamemode": True,
                        "use_mangohud": False,
                        "launch_args": "--from-profile",
                        "custom_env": {"DXVK_HUD": "0"},
                        "dlss_mode": "game_default",
                        "dlss_version": None,
                        "allow_unsupported_override": False,
                        "safety_mode": "strict",
                    },
                )
                save_install_override(
                    "steam:test-running",
                    {
                        **self._empty_override("steam:test-running"),
                        "sync_to_launcher": True,
                    },
                )

                result = launch_install("steam:test-running", "default")

        self.assertTrue(result["ok"], result["errors"])
        self.assertIsNone(result["pid"])
        self.assertTrue(any("automatic launch was skipped" in warning for warning in result["warnings"]))
        popen_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
