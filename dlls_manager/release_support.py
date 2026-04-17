from __future__ import annotations

from dlls_manager.models import LauncherInstallRecord, ReleaseSupportStatus, ResultSummary


_SOURCE_SUPPORT: dict[str, ReleaseSupportStatus] = {
    "steam": {
        "level": "supported",
        "note": "Primary release adapter for the first alpha. Discovery, planning, apply, launch, and rollback are release-signoff paths.",
    },
    "faugus": {
        "level": "advanced",
        "note": "Advanced-user adapter. Shipped for real workflows, but should be validated against the local install before trusting apply paths.",
    },
    "starcitizen_lug": {
        "level": "advanced",
        "note": "Advanced-user script-based adapter. Release candidate support depends on local validation of wrapper, script, and runner paths.",
    },
    "heroic": {
        "level": "experimental",
        "note": "Experimental adapter for the first alpha. Discovery is shipped, but real-install validation is not yet deep enough for broad support claims.",
    },
    "lutris": {
        "level": "experimental",
        "note": "Experimental adapter for the first alpha. Import support exists, but real-install validation is still limited.",
    },
    "bottles": {
        "level": "experimental",
        "note": "Experimental adapter for the first alpha. Discovery and sidecar sync exist, but release-grade validation is still pending.",
    },
    "desktop_entry": {
        "level": "experimental",
        "note": "Generic desktop-entry imports are intentionally conservative and should be treated as experimental until validated per install.",
    },
    "manual": {
        "level": "experimental",
        "note": "Manual imports are flexible by design and remain experimental for the first alpha.",
    },
}


def get_release_support(install: LauncherInstallRecord) -> ReleaseSupportStatus:
    support = _SOURCE_SUPPORT.get(install["source"])
    if support is None:
        return {
            "level": "experimental",
            "note": f"Unknown discovery source '{install['source']}' defaults to experimental release support.",
        }
    return dict(support)


def build_result_summary(
    install: LauncherInstallRecord | None,
    profile_name: str | None,
    compatibility_status: str | None,
    warnings: list[str],
    errors: list[str],
) -> ResultSummary:
    release_support = get_release_support(install)["level"] if install else None
    blocked = bool(errors) or compatibility_status == "blocked"
    return {
        "install_id": install["id"] if install else None,
        "display_name": install["display_name"] if install else None,
        "profile": profile_name,
        "release_support": release_support,
        "compatibility_status": compatibility_status,
        "warning_count": len(warnings),
        "error_count": len(errors),
        "blocked": blocked,
    }
