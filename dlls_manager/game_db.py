from pathlib import Path

from dlls_manager.models import ANTI_CHEAT_LEVELS, ANTI_CHEAT_POLICIES, OVERRIDE_MODES, GameRecord
from dlls_manager.paths import GAMES_FILE
from dlls_manager.utils import load_json


def validate_game(game: dict) -> GameRecord:
    if "id" not in game or "name" not in game:
        raise ValueError(f"Invalid game record: missing required keys in {game!r}")

    validated = dict(game)
    validated.setdefault("launcher", "manual")
    validated.setdefault("runtime", "unknown")
    validated.setdefault("anti_cheat", "unknown")
    validated.setdefault("anti_cheat_policy", "warn")
    validated.setdefault("anti_cheat_vendor", None)
    validated.setdefault("supports_dlss_override", False)
    validated.setdefault("supports_dlss_version_selection", False)
    validated.setdefault("override_mode", "experimental")
    validated.setdefault("notes", [])
    validated.setdefault("scan_path", None)

    if validated["anti_cheat"] not in ANTI_CHEAT_LEVELS:
        raise ValueError(
            f"Game '{validated['id']}' has invalid anti_cheat '{validated['anti_cheat']}'. "
            f"Expected one of: {', '.join(sorted(ANTI_CHEAT_LEVELS))}"
        )
    if validated["anti_cheat_policy"] not in ANTI_CHEAT_POLICIES:
        raise ValueError(
            f"Game '{validated['id']}' has invalid anti_cheat_policy '{validated['anti_cheat_policy']}'. "
            f"Expected one of: {', '.join(sorted(ANTI_CHEAT_POLICIES))}"
        )
    if validated["override_mode"] not in OVERRIDE_MODES:
        raise ValueError(
            f"Game '{validated['id']}' has invalid override_mode '{validated['override_mode']}'. "
            f"Expected one of: {', '.join(sorted(OVERRIDE_MODES))}"
        )
    if not isinstance(validated["supports_dlss_override"], bool):
        raise ValueError(f"Game '{validated['id']}' must define supports_dlss_override as a boolean.")
    if not isinstance(validated["supports_dlss_version_selection"], bool):
        raise ValueError(
            f"Game '{validated['id']}' must define supports_dlss_version_selection as a boolean."
        )
    if validated["anti_cheat_vendor"] is not None and not isinstance(validated["anti_cheat_vendor"], str):
        raise ValueError(f"Game '{validated['id']}' must define anti_cheat_vendor as a string or null.")
    if not isinstance(validated["notes"], list) or not all(isinstance(note, str) for note in validated["notes"]):
        raise ValueError(f"Game '{validated['id']}' must define notes as a list of strings.")
    if validated["scan_path"] is not None:
        validated["scan_path"] = str(Path(validated["scan_path"]))
    return validated


def load_games() -> list[GameRecord]:
    if not GAMES_FILE.exists():
        return []
    games = load_json(GAMES_FILE)
    if not isinstance(games, list):
        raise ValueError("games.json must contain a top-level array.")
    return [validate_game(game) for game in games]


def get_game(game_id: str) -> GameRecord:
    games = {game["id"]: game for game in load_games()}
    if game_id not in games:
        raise KeyError(f"Game ID '{game_id}' not found in games.json")
    return games[game_id]
