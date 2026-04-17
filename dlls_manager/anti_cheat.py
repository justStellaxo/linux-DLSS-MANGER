from pathlib import Path

from dlls_manager.models import (
    ANTI_CHEAT_LEVELS,
    ANTI_CHEAT_POLICIES,
    AntiCheatAssessment,
    AntiCheatRule,
    GameRecord,
    LauncherInstallRecord,
    MarkerHit,
)
from dlls_manager.paths import ANTI_CHEAT_RULES_FILE
from dlls_manager.utils import load_json


def validate_rule(rule: dict, index: int) -> AntiCheatRule:
    if "vendor" not in rule or not isinstance(rule["vendor"], str) or not rule["vendor"].strip():
        raise ValueError(f"anti_cheat_rules.json entry {index} must define a non-empty vendor string.")
    if "markers" not in rule or not isinstance(rule["markers"], list) or not rule["markers"]:
        raise ValueError(f"anti_cheat_rules.json entry {index} must define a non-empty markers list.")
    if not all(isinstance(marker, str) and marker for marker in rule["markers"]):
        raise ValueError(f"anti_cheat_rules.json entry {index} markers must be non-empty strings.")
    if rule.get("default_policy") not in ANTI_CHEAT_POLICIES:
        raise ValueError(
            f"anti_cheat_rules.json entry {index} has invalid default_policy '{rule.get('default_policy')}'."
        )
    anti_cheat_level = rule.get("anti_cheat_level", "high")
    if anti_cheat_level not in ANTI_CHEAT_LEVELS:
        raise ValueError(
            f"anti_cheat_rules.json entry {index} has invalid anti_cheat_level '{anti_cheat_level}'."
        )
    notes = rule.get("notes", "")
    if not isinstance(notes, str):
        raise ValueError(f"anti_cheat_rules.json entry {index} must define notes as a string.")
    return {
        "vendor": rule["vendor"],
        "markers": rule["markers"],
        "default_policy": rule["default_policy"],
        "anti_cheat_level": anti_cheat_level,
        "notes": notes,
    }


def load_rules() -> list[AntiCheatRule]:
    if not ANTI_CHEAT_RULES_FILE.exists():
        return []
    rules = load_json(ANTI_CHEAT_RULES_FILE)
    if not isinstance(rules, list):
        raise ValueError("anti_cheat_rules.json must contain a top-level array.")
    return [validate_rule(rule, index) for index, rule in enumerate(rules)]


def detect_markers(scan_path: str | None, rules: list[AntiCheatRule]) -> list[MarkerHit]:
    if not scan_path:
        return []

    root = Path(scan_path)
    if not root.exists():
        return []

    hits: list[MarkerHit] = []
    for rule in rules:
        for marker in rule["markers"]:
            if (root / marker).exists():
                hits.append(
                    {
                        "vendor": rule["vendor"],
                        "marker": marker,
                        "default_policy": rule["default_policy"],
                        "anti_cheat_level": rule["anti_cheat_level"],
                        "notes": rule["notes"],
                    }
                )
    return hits


def detect_markers_in_paths(scan_paths: list[str], rules: list[AntiCheatRule]) -> list[MarkerHit]:
    hits: list[MarkerHit] = []
    for scan_path in scan_paths:
        hits.extend(detect_markers(scan_path, rules))

    unique_hits: list[MarkerHit] = []
    seen: set[tuple[str, str]] = set()
    for hit in hits:
        key = (hit["vendor"], hit["marker"])
        if key in seen:
            continue
        seen.add(key)
        unique_hits.append(hit)
    return unique_hits


def classify_game(game: GameRecord) -> AntiCheatAssessment:
    rules = load_rules()
    reasons = []

    metadata_vendor = game.get("anti_cheat_vendor")
    metadata_policy = game.get("anti_cheat_policy", "warn")
    anti_cheat_level = game.get("anti_cheat", "unknown")

    marker_hits = detect_markers(game.get("scan_path"), rules)
    if marker_hits:
        primary = marker_hits[0]
        reasons.append(
            f"Detected anti-cheat marker '{primary['marker']}' for vendor {primary['vendor']}."
        )
        vendor = primary["vendor"]
        policy = primary["default_policy"]
        anti_cheat_level = primary["anti_cheat_level"]
        confidence = "high"
    elif metadata_vendor or anti_cheat_level != "unknown":
        vendor = metadata_vendor
        policy = metadata_policy
        confidence = "medium"
        reasons.append("Using anti-cheat metadata from games.json.")
    else:
        vendor = None
        policy = "warn"
        confidence = "low"
        reasons.append("No anti-cheat markers found; falling back to conservative default policy.")

    safe_actions = ["list", "preview", "ui_inspect"]
    blocked_actions = []
    if policy == "blocked":
        blocked_actions.extend(
            ["nvapi_override", "unsupported_override", "smooth_motion", "dlss_version_selection"]
        )
    elif policy == "warn":
        blocked_actions.append("smooth_motion")

    return {
        "vendor": vendor,
        "confidence": confidence,
        "policy": policy,
        "anti_cheat_level": anti_cheat_level,
        "reasons": reasons,
        "marker_hits": marker_hits,
        "safe_actions": safe_actions,
        "blocked_actions": blocked_actions,
    }


def classify_install(install: LauncherInstallRecord) -> AntiCheatAssessment:
    rules = load_rules()
    reasons = []
    marker_hits = detect_markers_in_paths(list(install.get("scan_paths", [])), rules)

    if marker_hits:
        primary = marker_hits[0]
        reasons.append(f"Detected anti-cheat marker '{primary['marker']}' for vendor {primary['vendor']}.")
        vendor = primary["vendor"]
        policy = primary["default_policy"]
        anti_cheat_level = primary["anti_cheat_level"]
        confidence = "high"
    elif install.get("anti_cheat_vendor") or install.get("anti_cheat") != "unknown":
        vendor = install.get("anti_cheat_vendor")
        policy = install.get("anti_cheat_policy", "warn")
        anti_cheat_level = install.get("anti_cheat", "unknown")
        confidence = "medium"
        reasons.append("Using installation metadata for anti-cheat classification.")
    else:
        vendor = None
        policy = "warn"
        anti_cheat_level = "unknown"
        confidence = "low"
        reasons.append("No anti-cheat markers found for the installation; falling back to conservative policy.")

    safe_actions = ["list", "preview", "ui_inspect", "validate"]
    blocked_actions = []
    if policy == "blocked":
        blocked_actions.extend(["nvapi_override", "unsupported_override", "smooth_motion", "dlss_version_selection"])
    elif policy == "warn":
        blocked_actions.append("smooth_motion")

    return {
        "vendor": vendor,
        "confidence": confidence,
        "policy": policy,
        "anti_cheat_level": anti_cheat_level,
        "reasons": reasons,
        "marker_hits": marker_hits,
        "safe_actions": safe_actions,
        "blocked_actions": blocked_actions,
    }
