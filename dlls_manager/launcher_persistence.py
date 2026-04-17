from __future__ import annotations

import shlex
from pathlib import Path

from dlls_manager.models import InstallOverride, LauncherInstallRecord, MutationStep
from dlls_manager.paths import BOTTLES_DIRS, FAUGUS_CONFIG_DIR, HEROIC_CONFIG_DIRS, LUTRIS_DIRS, STARCITIZEN_LUG_DIR, STEAM_ROOT_DIRS
from dlls_manager.utils import load_json


def _sidecar_payload(install: LauncherInstallRecord, profile_name: str, override: InstallOverride, effective_env: dict[str, str]) -> dict:
    return {
        "install_id": install["id"],
        "display_name": install["display_name"],
        "profile": profile_name,
        "override": override,
        "effective_env": effective_env,
    }


def _first_existing(paths: tuple[Path, ...]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _tokenize_vdf(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    in_string = False
    escape = False
    index = 0

    while index < len(text):
        char = text[index]

        if in_string:
            if escape:
                current.append(char)
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                tokens.append("".join(current))
                current = []
                in_string = False
            else:
                current.append(char)
            index += 1
            continue

        if char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            index = text.find("\n", index)
            if index == -1:
                break
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char in "{}":
            tokens.append(char)
        index += 1

    if in_string:
        raise ValueError("Unterminated quoted VDF string.")
    return tokens


def _parse_vdf_entries(tokens: list[str], index: int, terminate_on_closing_brace: bool) -> tuple[dict[str, object], int]:
    data: dict[str, object] = {}
    while index < len(tokens):
        token = tokens[index]
        if token == "}":
            if not terminate_on_closing_brace:
                raise ValueError("Unexpected closing brace at VDF root.")
            return data, index + 1
        if token == "{":
            raise ValueError("Unexpected opening brace in VDF block.")

        key = token
        index += 1
        if index >= len(tokens):
            raise ValueError(f"Missing value for VDF key '{key}'.")
        if tokens[index] == "{":
            nested, index = _parse_vdf_entries(tokens, index + 1, terminate_on_closing_brace=True)
            data[key] = nested
            continue
        if tokens[index] == "}":
            raise ValueError(f"Unexpected closing brace after VDF key '{key}'.")
        data[key] = tokens[index]
        index += 1
    if terminate_on_closing_brace:
        raise ValueError("Unterminated VDF block.")
    return data, index


def parse_vdf(text: str) -> dict[str, object]:
    tokens = _tokenize_vdf(text)
    data, index = _parse_vdf_entries(tokens, 0, terminate_on_closing_brace=False)
    if index != len(tokens):
        raise ValueError("Unexpected trailing VDF tokens.")
    return data


def _escape_vdf(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def dump_vdf(data: dict[str, object], indent: int = 0) -> str:
    prefix = "\t" * indent
    lines: list[str] = []
    for key, value in data.items():
        escaped_key = _escape_vdf(key)
        if isinstance(value, dict):
            lines.append(f'{prefix}"{escaped_key}"')
            lines.append(f"{prefix}{{")
            lines.append(dump_vdf(value, indent + 1))
            lines.append(f"{prefix}}}")
            continue
        lines.append(f'{prefix}"{escaped_key}"\t\t"{_escape_vdf(str(value))}"')
    return "\n".join(line for line in lines if line) + ("\n" if lines else "")


def _steam_localconfig_files() -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for root in STEAM_ROOT_DIRS:
        if not root.exists():
            continue
        for candidate in sorted(root.glob("userdata/*/config/localconfig.vdf")):
            normalized = str(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            files.append(candidate)
    return files


def _ensure_vdf_path(root: dict[str, object], *keys: str) -> dict[str, object]:
    current = root
    for key in keys:
        existing = current.get(key)
        if isinstance(existing, dict):
            current = existing
            continue
        replacement: dict[str, object] = {}
        current[key] = replacement
        current = replacement
    return current


def build_steam_launch_options(effective_env: dict[str, str], wrappers: list[str], launch_args: str) -> str:
    if not effective_env and not wrappers and not launch_args:
        return ""

    parts = [f"{key}={shlex.quote(value)}" for key, value in sorted(effective_env.items())]
    parts.extend(shlex.quote(wrapper) for wrapper in wrappers)
    parts.append("%command%")
    if launch_args:
        parts.extend(shlex.quote(arg) for arg in shlex.split(launch_args))
    return " ".join(parts)


def _steam_localconfig_payload(target: Path, app_id: str, launch_options: str) -> str:
    payload: dict[str, object]
    if target.exists():
        payload = parse_vdf(target.read_text(encoding="utf-8"))
    else:
        payload = {}

    apps = _ensure_vdf_path(payload, "UserLocalConfigStore", "Software", "Valve", "Steam", "apps")
    app_entry = _ensure_vdf_path(apps, app_id)
    if launch_options:
        app_entry["LaunchOptions"] = launch_options
    else:
        app_entry.pop("LaunchOptions", None)
    return dump_vdf(payload)


def _faugus_native_payload(install: LauncherInstallRecord, effective_env: dict[str, str], launch_args: str) -> list[dict] | None:
    games_file = FAUGUS_CONFIG_DIR / "games.json"
    if install["source"] != "faugus" or not games_file.exists():
        return None
    payload = load_json(games_file)
    if not isinstance(payload, list):
        return None

    updated: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            updated.append(item)
            continue
        current = dict(item)
        if str(current.get("gameid", "")).strip() == install["source_id"]:
            current["dlls_manager_profile"] = effective_env
            current["game_arguments"] = launch_args
        updated.append(current)
    return updated


def build_launcher_sync_steps(
    install: LauncherInstallRecord,
    profile_name: str,
    override: InstallOverride,
    effective_env: dict[str, str],
    effective_wrappers: list[str],
    launch_args: str,
) -> tuple[list[MutationStep], list[str], list[str]]:
    payload = _sidecar_payload(install, profile_name, override, effective_env)
    steps: list[MutationStep] = []
    warnings: list[str] = []
    blocked_reasons: list[str] = []

    if install["source"] == "faugus":
        sidecar_dir = FAUGUS_CONFIG_DIR / "dlls_manager_overrides"
        sidecar_path = sidecar_dir / f"{install['source_id']}.json"
        steps.append(
            {
                "id": f"sync-sidecar-{install['id']}",
                "action": "write_json",
                "description": "Write Faugus-sidecar override metadata.",
                "source_path": None,
                "target_path": str(sidecar_path),
                "payload": payload,
                "backup_required": True,
            }
        )
        native_payload = _faugus_native_payload(install, effective_env, launch_args)
        if native_payload is not None:
            steps.append(
                {
                    "id": f"sync-native-{install['id']}",
                    "action": "write_json",
                    "description": "Sync selected Faugus launch arguments into games.json.",
                    "source_path": None,
                    "target_path": str(FAUGUS_CONFIG_DIR / "games.json"),
                    "payload": native_payload,
                    "backup_required": True,
                }
            )
        return steps, warnings, blocked_reasons

    if install["source"] == "steam":
        app_id = install.get("app_id")
        if not app_id:
            blocked_reasons.append(f"Steam install '{install['display_name']}' is missing an app_id for launcher sync.")
            return steps, warnings, blocked_reasons

        steam_configs = _steam_localconfig_files()
        if not steam_configs:
            warnings.append("No Steam userdata localconfig.vdf files were found; Steam launch options were not synced.")
            return steps, warnings, blocked_reasons

        launch_options = build_steam_launch_options(effective_env, effective_wrappers, launch_args)
        for config_path in steam_configs:
            try:
                payload_text = _steam_localconfig_payload(config_path, str(app_id), launch_options)
            except Exception as exc:
                blocked_reasons.append(f"Failed to prepare Steam localconfig sync for {config_path}: {exc}")
                continue
            steps.append(
                {
                    "id": f"sync-steam-{install['id']}-{config_path.parent.parent.name}",
                    "action": "write_text",
                    "description": f"Sync Steam launch options for app {app_id} in {config_path.parent.parent.name}.",
                    "source_path": None,
                    "target_path": str(config_path),
                    "payload": payload_text,
                    "backup_required": True,
                }
            )
        return steps, warnings, blocked_reasons

    if install["source"] == "heroic":
        root = _first_existing(HEROIC_CONFIG_DIRS)
        if root:
            target = root / "dlls_manager_overrides" / f"{install['source_id']}.json"
            steps.append(
                {
                    "id": f"sync-heroic-{install['id']}",
                    "action": "write_json",
                    "description": "Write Heroic-sidecar override metadata.",
                    "source_path": None,
                    "target_path": str(target),
                    "payload": payload,
                    "backup_required": True,
                }
            )
        return steps, warnings, blocked_reasons

    if install["source"] == "lutris":
        root = _first_existing(LUTRIS_DIRS)
        if root:
            target = root / "dlls_manager_overrides" / f"{install['source_id']}.json"
            steps.append(
                {
                    "id": f"sync-lutris-{install['id']}",
                    "action": "write_json",
                    "description": "Write Lutris-sidecar override metadata.",
                    "source_path": None,
                    "target_path": str(target),
                    "payload": payload,
                    "backup_required": True,
                }
            )
        return steps, warnings, blocked_reasons

    if install["source"] == "bottles":
        bottle_root = Path(install["prefix_path"]) if install.get("prefix_path") else _first_existing(BOTTLES_DIRS)
        if bottle_root:
            target = bottle_root / "dlls_manager_override.json"
            steps.append(
                {
                    "id": f"sync-bottles-{install['id']}",
                    "action": "write_json",
                    "description": "Write Bottles-sidecar override metadata.",
                    "source_path": None,
                    "target_path": str(target),
                    "payload": payload,
                    "backup_required": True,
                }
            )
        return steps, warnings, blocked_reasons

    if install["source"] == "starcitizen_lug":
        target = STARCITIZEN_LUG_DIR / "dlls_manager_overrides" / f"{install['source_id']}.json"
        steps.append(
            {
                "id": f"sync-rsi-{install['id']}",
                "action": "write_json",
                "description": "Write Star-Citizen-LUG-sidecar override metadata.",
                "source_path": None,
                "target_path": str(target),
                "payload": payload,
                "backup_required": True,
            }
        )
        return steps, warnings, blocked_reasons

    return steps, warnings, blocked_reasons
