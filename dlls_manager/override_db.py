from __future__ import annotations

from pathlib import Path

from dlls_manager.models import InstallOverride
from dlls_manager.paths import INSTALL_OVERRIDES_DIR
from dlls_manager.utils import atomic_write_json, load_json


def install_override_path(install_id: str) -> Path:
    safe_id = install_id.replace("/", "_").replace(":", "__")
    return INSTALL_OVERRIDES_DIR / f"{safe_id}.json"


def validate_install_override(install_id: str, payload: dict | None) -> InstallOverride:
    data = dict(payload or {})
    data.setdefault("install_id", install_id)
    data.setdefault("extra_env", {})
    data.setdefault("extra_wrappers", [])
    data.setdefault("launch_args", "")
    data.setdefault("dlss_version", None)
    data.setdefault("enable_nvapi", None)
    data.setdefault("enable_smooth_motion", None)
    data.setdefault("use_gamemode", None)
    data.setdefault("use_mangohud", None)
    data.setdefault("allow_unsupported_override", None)
    data.setdefault("sync_to_launcher", True)
    data.setdefault("dlss_target_path", None)
    data.setdefault("notes", [])

    if data["install_id"] != install_id:
        raise ValueError(f"Install override payload install_id mismatch: {data['install_id']} != {install_id}")
    if not isinstance(data["extra_env"], dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in data["extra_env"].items()
    ):
        raise ValueError("Install override extra_env must be a string-to-string object.")
    if not isinstance(data["extra_wrappers"], list) or not all(isinstance(item, str) for item in data["extra_wrappers"]):
        raise ValueError("Install override extra_wrappers must be a string list.")
    if not isinstance(data["launch_args"], str):
        raise ValueError("Install override launch_args must be a string.")
    if data["dlss_version"] is not None and not isinstance(data["dlss_version"], str):
        raise ValueError("Install override dlss_version must be a string or null.")
    for key in (
        "enable_nvapi",
        "enable_smooth_motion",
        "use_gamemode",
        "use_mangohud",
        "allow_unsupported_override",
    ):
        if data[key] is not None and not isinstance(data[key], bool):
            raise ValueError(f"Install override {key} must be a boolean or null.")
    if not isinstance(data["sync_to_launcher"], bool):
        raise ValueError("Install override sync_to_launcher must be a boolean.")
    if data["dlss_target_path"] is not None and not isinstance(data["dlss_target_path"], str):
        raise ValueError("Install override dlss_target_path must be a string or null.")
    if not isinstance(data["notes"], list) or not all(isinstance(item, str) for item in data["notes"]):
        raise ValueError("Install override notes must be a string list.")
    return data  # type: ignore[return-value]


def load_install_override(install_id: str) -> InstallOverride:
    path = install_override_path(install_id)
    if not path.exists():
        return validate_install_override(install_id, {})
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Install override '{install_id}' must contain a top-level object.")
    return validate_install_override(install_id, payload)


def save_install_override(install_id: str, payload: dict) -> InstallOverride:
    validated = validate_install_override(install_id, payload)
    atomic_write_json(install_override_path(install_id), validated)
    return validated


def _coerce_bool(raw_value: str) -> bool:
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw_value}")


def update_install_override(install_id: str, updates: dict[str, str]) -> InstallOverride:
    current = dict(load_install_override(install_id))
    for key, raw_value in updates.items():
        if key.startswith("extra_env."):
            env_key = key.split(".", 1)[1]
            current.setdefault("extra_env", {})
            current["extra_env"][env_key] = raw_value
            continue
        if key == "extra_wrappers":
            current[key] = [item.strip() for item in raw_value.split(",") if item.strip()]
            continue
        if key in {
            "enable_nvapi",
            "enable_smooth_motion",
            "use_gamemode",
            "use_mangohud",
            "allow_unsupported_override",
            "sync_to_launcher",
        }:
            current[key] = _coerce_bool(raw_value)
            continue
        if key in {"dlss_version", "dlss_target_path"}:
            current[key] = None if raw_value.strip().lower() in {"", "none", "null"} else raw_value
            continue
        if key == "notes":
            current[key] = [item.strip() for item in raw_value.split("|") if item.strip()]
            continue
        current[key] = raw_value
    return save_install_override(install_id, current)


def list_install_overrides() -> list[str]:
    if not INSTALL_OVERRIDES_DIR.exists():
        return []
    install_ids: list[str] = []
    for path in sorted(INSTALL_OVERRIDES_DIR.glob("*.json")):
        install_id = path.stem.replace("__", ":")
        install_ids.append(install_id)
    return install_ids
