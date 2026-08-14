from pathlib import Path

from dlls_manager.models import Profile, SAFETY_MODES
from dlls_manager.paths import PROFILES_DIR
from dlls_manager.utils import atomic_write_json, load_json


def validate_profile(profile_name: str, profile: dict) -> Profile:
    validated = dict(profile)
    validated.setdefault("enable_nvapi", False)
    validated.setdefault("enable_smooth_motion", False)
    validated.setdefault("use_gamemode", False)
    validated.setdefault("use_mangohud", False)
    validated.setdefault("launch_args", "")
    validated.setdefault("custom_env", {})
    validated.setdefault("dlss_mode", "game_default")
    validated.setdefault("dlss_version", None)
    validated.setdefault("allow_unsupported_override", False)
    validated.setdefault("safety_mode", "strict")
    validated.setdefault("dlss_sr_preset", None)
    validated.setdefault("dlss_rr_preset", None)
    validated.setdefault("dlss_fg_override", None)
    validated.setdefault("enable_ngx_updater", False)
    validated.setdefault("enable_hags", False)
    validated.setdefault("enable_vkreflex", False)
    validated.setdefault("proton_dlss_upgrade", None)

    if validated["safety_mode"] not in SAFETY_MODES:
        raise ValueError(
            f"Profile '{profile_name}' has invalid safety_mode '{validated['safety_mode']}'. "
            f"Expected one of: {', '.join(sorted(SAFETY_MODES))}"
        )
    for key in ("enable_nvapi", "enable_smooth_motion", "use_gamemode", "use_mangohud", "allow_unsupported_override",
                "enable_ngx_updater", "enable_hags", "enable_vkreflex"):
        if not isinstance(validated[key], bool):
            raise ValueError(f"Profile '{profile_name}' must define {key} as a boolean.")
    if not isinstance(validated["custom_env"], dict):
        raise ValueError(f"Profile '{profile_name}' must define custom_env as an object.")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in validated["custom_env"].items()):
        raise ValueError(f"Profile '{profile_name}' must define custom_env as a string-to-string object.")
    if not isinstance(validated["launch_args"], str):
        raise ValueError(f"Profile '{profile_name}' must define launch_args as a string.")
    if not isinstance(validated["dlss_mode"], str):
        raise ValueError(f"Profile '{profile_name}' must define dlss_mode as a string.")
    if validated["dlss_version"] is not None and not isinstance(validated["dlss_version"], str):
        raise ValueError(f"Profile '{profile_name}' must define dlss_version as a string or null.")
    return validated


def load_profile(profile_name: str) -> Profile:
    path = PROFILES_DIR / f"{profile_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    profile = load_json(path)
    if not isinstance(profile, dict):
        raise ValueError(f"Profile '{profile_name}' must contain a top-level object.")
    return validate_profile(profile_name, profile)


def list_profiles() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(path.stem for path in PROFILES_DIR.glob("*.json"))


def load_profiles() -> dict[str, Profile]:
    return {name: load_profile(name) for name in list_profiles()}


def save_profile(profile_name: str, profile: dict) -> Profile:
    validated = validate_profile(profile_name, profile)
    path = PROFILES_DIR / f"{profile_name}.json"
    atomic_write_json(path, validated)
    return validated


def _coerce_profile_value(key: str, raw_value: str):
    bool_fields = {
        "enable_nvapi",
        "enable_smooth_motion",
        "use_gamemode",
        "use_mangohud",
        "allow_unsupported_override",
    }
    if key in bool_fields:
        normalized = raw_value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"Invalid boolean value for {key}: {raw_value}")
    if key == "dlss_version":
        return None if raw_value.strip().lower() in {"", "none", "null"} else raw_value
    return raw_value


def update_profile(profile_name: str, updates: dict[str, str]) -> Profile:
    current = dict(load_profile(profile_name))
    for key, raw_value in updates.items():
        if key.startswith("custom_env."):
            env_key = key.split(".", 1)[1]
            current.setdefault("custom_env", {})
            current["custom_env"][env_key] = raw_value
            continue
        current[key] = _coerce_profile_value(key, raw_value)
    return save_profile(profile_name, current)


def apply_profile_updates(profile_name: str, updates: dict) -> Profile:
    current = dict(load_profile(profile_name))
    for key, value in updates.items():
        if key == "custom_env":
            if not isinstance(value, dict):
                raise ValueError("custom_env must be an object.")
            current[key] = value
            continue
        if key == "dlss_version":
            current[key] = None if value in {"", None, "none", "null"} else value
            continue
        current[key] = value
    return save_profile(profile_name, current)


def profile_path(profile_name: str) -> Path:
    return PROFILES_DIR / f"{profile_name}.json"
