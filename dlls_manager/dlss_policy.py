from dlls_manager.dlss_catalog import load_dlss_versions, validate_dlss_version
from dlls_manager.models import DlssPolicyEvaluation, GameRecord, OverrideMode, Profile


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
