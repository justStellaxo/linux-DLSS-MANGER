import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from dlls_manager.launch_plan import build_install_launch_plan
from dlls_manager.launcher_runtime import launch_install
from dlls_manager.override_db import save_install_override
from dlls_manager.profile_db import save_profile

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


class WrapperRuntimeTests(unittest.TestCase):
    def _profile(self, use_gamemode: bool = False, use_mangohud: bool = False, launch_args: str = "", custom_env: dict | None = None) -> dict:
        return {
            "enable_nvapi": False,
            "enable_smooth_motion": False,
            "use_gamemode": use_gamemode,
            "use_mangohud": use_mangohud,
            "launch_args": launch_args,
            "custom_env": custom_env or {},
            "dlss_mode": "game_default",
            "dlss_version": None,
            "allow_unsupported_override": False,
            "safety_mode": "strict",
        }

    def _empty_override(self, install_id: str, *, sync_to_launcher: bool = False) -> dict:
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
            "sync_to_launcher": sync_to_launcher,
            "dlss_target_path": None,
            "notes": [],
        }

    def test_launch_executes_fake_wrapper_chain_for_manual_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            bin_dir = root / "bin"
            game_dir = root / "game"
            bin_dir.mkdir()
            game_dir.mkdir()
            profiles_dir.mkdir()

            gamemode_marker = root / "gamemode.marker"
            mangohud_marker = root / "mangohud.marker"
            args_file = root / "args.txt"
            env_file = root / "env.txt"

            _write_executable(
                bin_dir / "gamemoderun",
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -eu
                    printf 'gamemoderun' > {gamemode_marker}
                    exec "$@"
                    """
                ),
            )
            _write_executable(
                bin_dir / "mangohud",
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -eu
                    printf 'mangohud' > {mangohud_marker}
                    exec "$@"
                    """
                ),
            )
            _write_executable(
                game_dir / "run.sh",
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -eu
                    printf '%s' "$*" > {args_file}
                    printf '%s' "${{TEST_FLAG:-}}" > {env_file}
                    """
                ),
            )

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-19T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "manual:test-wrapper-chain",
                                "display_name": "Wrapper Chain Test",
                                "source": "manual",
                                "source_id": "test-wrapper-chain",
                                "launcher_family": "manual",
                                "store_family": "generic",
                                "execution_strategy": "script_exec",
                                "runtime": "native",
                                "install_root": str(game_dir),
                                "prefix_path": None,
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": str(game_dir / "run.sh"),
                                "desktop_file": None,
                                "app_id": None,
                                "launch_command": [str(game_dir / "run.sh")],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": [],
                                "working_directory": str(game_dir),
                                "scan_paths": [str(game_dir)],
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

            with patch.dict(os.environ, {"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}), patch(
                "dlls_manager.install_db.INSTALLS_FILE", installs_file
            ), patch("dlls_manager.profile_db.PROFILES_DIR", profiles_dir), patch(
                "dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir
            ), patch("dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir):
                save_profile("default", self._profile(use_gamemode=True, use_mangohud=True, launch_args="--from-profile", custom_env={"TEST_FLAG": "wrapper-ok"}))
                result = launch_install("manual:test-wrapper-chain", "default", wait=True)

                self.assertTrue(result["ok"], result["errors"])
                self.assertEqual(gamemode_marker.read_text(encoding="utf-8"), "gamemoderun")
                self.assertEqual(mangohud_marker.read_text(encoding="utf-8"), "mangohud")
                self.assertEqual(args_file.read_text(encoding="utf-8"), "--from-profile")
                self.assertEqual(env_file.read_text(encoding="utf-8"), "wrapper-ok")

    def test_manual_launch_fails_when_requested_wrapper_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            game_dir = root / "game"
            game_dir.mkdir()
            profiles_dir.mkdir()

            _write_executable(
                game_dir / "run.sh",
                "#!/usr/bin/env bash\nexit 0\n",
            )

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-19T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "manual:test-missing-wrapper",
                                "display_name": "Missing Wrapper Test",
                                "source": "manual",
                                "source_id": "test-missing-wrapper",
                                "launcher_family": "manual",
                                "store_family": "generic",
                                "execution_strategy": "script_exec",
                                "runtime": "native",
                                "install_root": str(game_dir),
                                "prefix_path": None,
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": str(game_dir / "run.sh"),
                                "desktop_file": None,
                                "app_id": None,
                                "launch_command": [str(game_dir / "run.sh")],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": [],
                                "working_directory": str(game_dir),
                                "scan_paths": [str(game_dir)],
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

            with patch.dict(os.environ, {"PATH": str(game_dir)}), patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir):
                save_profile("default", self._profile(use_mangohud=True))
                plan = build_install_launch_plan("manual:test-missing-wrapper", "default")
                result = launch_install("manual:test-missing-wrapper", "default", wait=True)

        self.assertEqual(plan["compatibility_status"], "warn")
        self.assertTrue(any("mangohud" in warning for warning in plan["warnings"]))
        self.assertFalse(result["ok"])
        self.assertTrue(any("mangohud" in error for error in result["errors"]))

    def test_gamescope_and_mangohud_is_blocked_until_mangoapp_flow_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            game_dir = root / "game"
            bin_dir = root / "bin"
            game_dir.mkdir()
            bin_dir.mkdir()
            profiles_dir.mkdir()

            _write_executable(bin_dir / "gamescope", "#!/usr/bin/env bash\nexec \"$@\"\n")
            _write_executable(bin_dir / "mangohud", "#!/usr/bin/env bash\nexec \"$@\"\n")
            _write_executable(
                game_dir / "run.sh",
                "#!/usr/bin/env bash\nexit 0\n",
            )

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-19T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "manual:test-gamescope",
                                "display_name": "gamescope Test",
                                "source": "manual",
                                "source_id": "test-gamescope",
                                "launcher_family": "manual",
                                "store_family": "generic",
                                "execution_strategy": "script_exec",
                                "runtime": "native",
                                "install_root": str(game_dir),
                                "prefix_path": None,
                                "runner_name": None,
                                "runner_path": None,
                                "exe_path": None,
                                "script_path": str(game_dir / "run.sh"),
                                "desktop_file": None,
                                "app_id": None,
                                "launch_command": [str(game_dir / "run.sh")],
                                "launch_env": {},
                                "launch_args": "",
                                "wrapper_chain": ["gamescope"],
                                "working_directory": str(game_dir),
                                "scan_paths": [str(game_dir)],
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

            with patch.dict(os.environ, {"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}), patch(
                "dlls_manager.install_db.INSTALLS_FILE", installs_file
            ), patch("dlls_manager.profile_db.PROFILES_DIR", profiles_dir), patch(
                "dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir
            ):
                save_profile("default", self._profile(use_mangohud=True))
                plan = build_install_launch_plan("manual:test-gamescope", "default")

        self.assertEqual(plan["compatibility_status"], "blocked")
        self.assertTrue(any("gamescope-backed launches" in reason for reason in plan["blocked_reasons"]))

    def test_fake_steam_executes_localconfig_launch_options_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installs_file = root / "installs.json"
            profiles_dir = root / "profiles"
            overrides_dir = root / "overrides"
            rollbacks_dir = root / "rollbacks"
            steam_root = root / "Steam"
            localconfig = steam_root / "userdata" / "1000" / "config" / "localconfig.vdf"
            bin_dir = root / "bin"
            game_dir = root / "game"
            localconfig.parent.mkdir(parents=True)
            localconfig.write_text("", encoding="utf-8")
            bin_dir.mkdir()
            game_dir.mkdir()
            profiles_dir.mkdir()

            gamemode_marker = root / "steam-gamemode.marker"
            mangohud_marker = root / "steam-mangohud.marker"
            args_file = root / "steam-args.txt"
            env_file = root / "steam-env.txt"

            _write_executable(
                bin_dir / "gamemoderun",
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -eu
                    printf 'gamemoderun' > {gamemode_marker}
                    exec "$@"
                    """
                ),
            )
            _write_executable(
                bin_dir / "mangohud",
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -eu
                    printf 'mangohud' > {mangohud_marker}
                    exec "$@"
                    """
                ),
            )
            _write_executable(
                game_dir / "run.sh",
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -eu
                    printf '%s' "$*" > {args_file}
                    printf '%s' "${{TEST_FLAG:-}}" > {env_file}
                    """
                ),
            )
            _write_executable(
                bin_dir / "steam",
                textwrap.dedent(
                    f"""\
                    #!{sys.executable}
                    import os
                    import shlex
                    import subprocess
                    import sys
                    from pathlib import Path

                    sys.path.insert(0, {str(PROJECT_ROOT)!r})
                    from dlls_manager.launcher_persistence import parse_vdf

                    if len(sys.argv) < 3 or sys.argv[1] != "-applaunch":
                        raise SystemExit(2)

                    app_id = sys.argv[2]
                    localconfig = Path(os.environ["DLLS_MANAGER_FAKE_STEAM_LOCALCONFIG"])
                    game_command = shlex.split(os.environ["DLLS_MANAGER_FAKE_STEAM_COMMAND"])
                    payload = parse_vdf(localconfig.read_text(encoding="utf-8"))
                    launch_options = payload["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][app_id]["LaunchOptions"]

                    before: list[str] = []
                    after: list[str] = []
                    command_tokens = shlex.split(launch_options)
                    saw_command = False
                    for token in command_tokens:
                        if token == "%command%":
                            saw_command = True
                            continue
                        if not saw_command:
                            before.append(token)
                        else:
                            after.append(token)

                    env = os.environ.copy()
                    command: list[str] = []
                    for token in before:
                        if "=" in token and token.split("=", 1)[0].replace("_", "").isalnum():
                            key, value = token.split("=", 1)
                            env[key] = value
                        else:
                            command.append(token)

                    command.extend(game_command)
                    command.extend(after)
                    raise SystemExit(subprocess.run(command, env=env, check=False).returncode)
                    """
                ),
            )

            installs_file.write_text(
                json.dumps(
                    {
                        "created_at": "2026-04-19T00:00:00Z",
                        "warnings": [],
                        "installs": [
                            {
                                "id": "steam:test-fake-runtime",
                                "display_name": "Fake Steam Runtime Test",
                                "source": "steam",
                                "source_id": "test-fake-runtime",
                                "launcher_family": "steam",
                                "store_family": "steam",
                                "execution_strategy": "steam_app",
                                "runtime": "proton-dx11",
                                "install_root": str(game_dir),
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
                                "working_directory": str(game_dir),
                                "scan_paths": [str(game_dir)],
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

            fake_steam_env = {
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                "DLLS_MANAGER_FAKE_STEAM_LOCALCONFIG": str(localconfig),
                "DLLS_MANAGER_FAKE_STEAM_COMMAND": str(game_dir / "run.sh"),
            }
            with patch.dict(os.environ, fake_steam_env), patch("dlls_manager.install_db.INSTALLS_FILE", installs_file), patch(
                "dlls_manager.profile_db.PROFILES_DIR", profiles_dir
            ), patch("dlls_manager.override_db.INSTALL_OVERRIDES_DIR", overrides_dir), patch(
                "dlls_manager.mutations.base.ROLLBACKS_DIR", rollbacks_dir
            ), patch("dlls_manager.launcher_persistence.STEAM_ROOT_DIRS", (steam_root,)), patch(
                "dlls_manager.launcher_runtime._steam_is_running", return_value=False
            ):
                save_profile(
                    "default",
                    self._profile(use_gamemode=True, use_mangohud=True, launch_args="--steam-arg", custom_env={"TEST_FLAG": "steam-ok"}),
                )
                save_install_override(
                    "steam:test-fake-runtime",
                    self._empty_override("steam:test-fake-runtime", sync_to_launcher=True),
                )
                result = launch_install("steam:test-fake-runtime", "default", wait=True)

                self.assertTrue(result["ok"], result["errors"])
                self.assertEqual(gamemode_marker.read_text(encoding="utf-8"), "gamemoderun")
                self.assertEqual(mangohud_marker.read_text(encoding="utf-8"), "mangohud")
                self.assertEqual(args_file.read_text(encoding="utf-8"), "--steam-arg")
                self.assertEqual(env_file.read_text(encoding="utf-8"), "steam-ok")


if __name__ == "__main__":
    unittest.main()
