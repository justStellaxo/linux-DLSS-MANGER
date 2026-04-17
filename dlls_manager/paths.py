from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOME_DIR = Path.home()
PROFILES_DIR = PROJECT_ROOT / "profiles"
INSTALL_OVERRIDES_DIR = PROJECT_ROOT / "install_overrides"
ROLLBACKS_DIR = PROJECT_ROOT / "rollbacks"
DLSS_RUNTIME_DIR = PROJECT_ROOT / "dlss_runtime"
DLSS_DOWNLOADS_DIR = PROJECT_ROOT / "dlss_downloads"
GAMES_FILE = PROJECT_ROOT / "games.json"
ANTI_CHEAT_RULES_FILE = PROJECT_ROOT / "anti_cheat_rules.json"
DLSS_VERSIONS_FILE = PROJECT_ROOT / "dlss_versions.json"
SNAPSHOTS_DIR = PROJECT_ROOT / "snapshots"
INSTALLS_FILE = PROJECT_ROOT / "installs.json"
MOCK_UI_DIR = PROJECT_ROOT / "mock_ui"
MOCK_UI_DATA_FILE = MOCK_UI_DIR / "mock-library.json"
MOCK_UI_SCRIPT_FILE = MOCK_UI_DIR / "mock-library.js"
LOCAL_APPLICATIONS_DIR = HOME_DIR / ".local" / "share" / "applications"
FAUGUS_CONFIG_DIR = HOME_DIR / ".config" / "faugus-launcher"
FAUGUS_GAMES_FILE = FAUGUS_CONFIG_DIR / "games.json"
STARCITIZEN_LUG_DIR = HOME_DIR / ".config" / "starcitizen-lug"
HEROIC_CONFIG_DIRS = (
    HOME_DIR / ".config" / "heroic",
    HOME_DIR / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic",
)
LUTRIS_DIRS = (
    HOME_DIR / ".config" / "lutris",
    HOME_DIR / ".local" / "share" / "lutris",
    HOME_DIR / ".var" / "app" / "net.lutris.Lutris" / "data" / "lutris",
)
BOTTLES_DIRS = (
    HOME_DIR / ".local" / "share" / "bottles",
    HOME_DIR / ".var" / "app" / "com.usebottles.bottles" / "data" / "bottles",
)
STEAM_ROOT_DIRS = (
    HOME_DIR / ".steam" / "steam",
    HOME_DIR / ".local" / "share" / "Steam",
    HOME_DIR / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
)
