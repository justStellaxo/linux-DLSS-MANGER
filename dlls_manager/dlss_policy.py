from dlls_manager.models import DlssPolicyEvaluation, DlssVersionRecord, GameRecord, OverrideMode, Profile
from dlls_manager.paths import DLSS_VERSIONS_FILE
from dlls_manager.utils import load_json


def validate_dlss_version(item: dict, index: int) -> DlssVersionRecord:
    if "id" not in item or not isinstance(item["id"], str) or not item["id"].strip():
        raise ValueError(f"dlss_versions.json entry {index} must define a non-empty id string.")
    if "label" not in item or not isinstance(item["label"], str) or not item["label"].strip():
        raise ValueError(f"dlss_versions.json entry {index} must define a non-empty label string.")
    selectable = item.get("selectable")
    if not isinstance(selectable, bool):
        raise ValueError(f"dlss_versions.json entry {index} must define selectable as a boolean.")
    return {"id": item["id"], "label": item["label"], "selectable": selectable}


def load_dlss_versions() -> list[DlssVersionRecord]:
    if not DLSS_VERSIONS_FILE.exists():
        return []
    versions = load_json(DLSS_VERSIONS_FILE)
    if not isinstance(versions, list):
        raise ValueError("dlss_versions.json must contain a top-level array.")
    return [validate_dlss_version(item, index) for index, item in enumerate(versions)]


def evaluate_dlss_policy(game: GameRecord, profile: Profile) -> DlssPolicyEvaluation:
    warnings = []
    blocked_reasons = []
    selected_version = profile.get("dlss_version")
    version_catalog = {item["id"]: item for item in load_dlss_versions()}

    if selected_version and selected_version not in version_catalog:
        blocked_reasons.append(f"DLSS version '{selected_version}' is not present in dlss_versions.json.")
    elif selected_version and not version_catalog[selected_version]["selectable"]:
        blocked_reasons.append(f"DLSS version '{selected_version}' is not marked as selectable.")

    if selected_version and not game.get("supports_dlss_version_selection", False):
        blocked_reasons.append(
            f"Game '{game['id']}' is not marked as supporting DLSS version selection."
        )

    override_mode: OverrideMode = game.get("override_mode", "experimental")
    if profile.get("allow_unsupported_override") and override_mode == "blocked":
        blocked_reasons.append(f"Game '{game['id']}' blocks unsupported override attempts.")
    elif profile.get("allow_unsupported_override") and override_mode != "blocked":
        warnings.append(f"Game '{game['id']}' will treat unsupported overrides as experimental.")

    return {
        "selected_version": selected_version,
        "warnings": warnings,
        "blocked_reasons": blocked_reasons,
    }
