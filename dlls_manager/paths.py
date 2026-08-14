import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOME_DIR = Path.home()


def _path_override(env_name: str, default: Path) -> Path:
    env_value = os.environ.get(env_name)
    if env_value:
        return Path(env_value).expanduser()
    return Path(default).expanduser()


PROFILES_DIR = _path_override("DLLS_MANAGER_PROFILES_DIR", PROJECT_ROOT / "profiles")
INSTALL_OVERRIDES_DIR = _path_override("DLLS_MANAGER_INSTALL_OVERRIDES_DIR", PROJECT_ROOT / "install_overrides")
ROLLBACKS_DIR = _path_override("DLLS_MANAGER_ROLLBACKS_DIR", PROJECT_ROOT / "rollbacks")
DLSS_RUNTIME_DIR = _path_override("DLLS_MANAGER_DLSS_RUNTIME_DIR", PROJECT_ROOT / "dlss_runtime")
DLSS_DOWNLOADS_DIR = _path_override("DLLS_MANAGER_DLSS_DOWNLOADS_DIR", PROJECT_ROOT / "dlss_downloads")
SNAPSHOTS_DIR = _path_override("DLLS_MANAGER_SNAPSHOTS_DIR", PROJECT_ROOT / "snapshots")
GAMES_FILE = _path_override("DLLS_MANAGER_GAMES_FILE", PROJECT_ROOT / "games.json")
ANTI_CHEAT_RULES_FILE = _path_override("DLLS_MANAGER_ANTI_CHEAT_RULES_FILE", PROJECT_ROOT / "anti_cheat_rules.json")
DLSS_VERSIONS_FILE = _path_override("DLLS_MANAGER_DLSS_VERSIONS_FILE", PROJECT_ROOT / "dlss_versions.json")
INSTALLS_FILE = _path_override("DLLS_MANAGER_INSTALLS_FILE", PROJECT_ROOT / "installs.json")
LOCAL_APPLICATIONS_DIR = _path_override("DLLS_MANAGER_LOCAL_APPLICATIONS_DIR", HOME_DIR / ".local" / "share" / "applications")
FAUGUS_CONFIG_DIR = _path_override("DLLS_MANAGER_FAUGUS_CONFIG_DIR", HOME_DIR / ".config" / "faugus-launcher")
FAUGUS_GAMES_FILE = _path_override("DLLS_MANAGER_FAUGUS_GAMES_FILE", FAUGUS_CONFIG_DIR / "games.json")
STARCITIZEN_LUG_DIR = _path_override("DLLS_MANAGER_STARCITIZEN_LUG_DIR", HOME_DIR / ".config" / "starcitizen-lug")
HEROIC_CONFIG_DIRS = (
    _path_override("DLLS_MANAGER_HEROIC_CONFIG_DIR_1", HOME_DIR / ".config" / "heroic"),
    _path_override("DLLS_MANAGER_HEROIC_CONFIG_DIR_2", HOME_DIR / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic"),
)
LUTRIS_DIRS = (
    _path_override("DLLS_MANAGER_LUTRIS_DIR_1", HOME_DIR / ".config" / "lutris"),
    _path_override("DLLS_MANAGER_LUTRIS_DIR_2", HOME_DIR / ".local" / "share" / "lutris"),
    _path_override("DLLS_MANAGER_LUTRIS_DIR_3", HOME_DIR / ".var" / "app" / "net.lutris.Lutris" / "data" / "lutris"),
)
BOTTLES_DIRS = (
    _path_override("DLLS_MANAGER_BOTTLES_DIR_1", HOME_DIR / ".local" / "share" / "bottles"),
    _path_override("DLLS_MANAGER_BOTTLES_DIR_2", HOME_DIR / ".var" / "app" / "com.usebottles.bottles" / "data" / "bottles"),
)
STEAM_ROOT_DIRS = (
    _path_override("DLLS_MANAGER_STEAM_ROOT_DIR_1", HOME_DIR / ".steam" / "steam"),
    _path_override("DLLS_MANAGER_STEAM_ROOT_DIR_2", HOME_DIR / ".local" / "share" / "Steam"),
    _path_override("DLLS_MANAGER_STEAM_ROOT_DIR_3", HOME_DIR / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam"),
)
