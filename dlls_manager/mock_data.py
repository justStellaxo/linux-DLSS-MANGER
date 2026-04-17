from datetime import datetime, timezone

from dlls_manager.detector import detect_capabilities
from dlls_manager.dlss_policy import load_dlss_versions
from dlls_manager.install_db import load_installs
from dlls_manager.launch_plan import build_install_launch_plan, explain_install_policy
from dlls_manager.mutations import list_rollbacks
from dlls_manager.override_db import load_install_override
from dlls_manager.profile_db import list_profiles, load_profile
from dlls_manager.utils import dump_json


def export_mock_library() -> dict:
    profiles = list_profiles()
    if not profiles:
        return {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "profiles": [],
            "default_profile": None,
            "capabilities": detect_capabilities(),
            "games": [],
        }

    default_profile = "default" if "default" in profiles else profiles[0]
    capabilities = detect_capabilities()
    installs = load_installs()
    dlss_versions = load_dlss_versions()
    rollbacks = list_rollbacks()
    entries = []
    for install in installs:
        profile_views = {}
        for profile_name in profiles:
            launch_plan = build_install_launch_plan(install["id"], profile_name)
            profile_views[profile_name] = {
                "profile_config": load_profile(profile_name),
                "effective_profile_config": launch_plan["effective_profile_config"],
                "launch_plan": launch_plan,
                "policy_report": explain_install_policy(install["id"], profile_name),
            }

        entries.append(
            {
                "id": install["id"],
                "name": install["display_name"],
                "launcher": install["launcher_family"],
                "runtime": install["runtime"],
                "notes": install["notes"],
                "supports_dlss_override": install["supports_dlss_override"],
                "supports_dlss_version_selection": install["supports_dlss_version_selection"],
                "override_mode": install["override_mode"],
                "release_support": profile_views[default_profile]["launch_plan"]["release_support"],
                "default_profile": default_profile,
                "override_config": load_install_override(install["id"]),
                "cli_commands": {
                    "prepare": f"python3 main.py prepare-launch --install-id {install['id']} --profile {default_profile}",
                    "apply": f"python3 main.py apply --install-id {install['id']} --profile {default_profile}",
                    "launch": f"python3 main.py launch --install-id {install['id']} --profile {default_profile}",
                },
                "library_summary": {
                    "source": install["source"],
                    "store_family": install["store_family"],
                    "execution_strategy": install["execution_strategy"],
                    "install_root": install["install_root"],
                    "prefix_path": install["prefix_path"],
                    "runner_name": install["runner_name"],
                    "validation_errors": install["validation_errors"],
                    "validation_warnings": install["validation_warnings"],
                },
                "profiles": profile_views,
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profiles": profiles,
        "default_profile": default_profile,
        "dlss_versions": dlss_versions,
        "rollbacks": rollbacks,
        "capabilities": capabilities,
        "games": entries,
    }


def build_mock_ui_script(payload: dict) -> str:
    return f"window.MOCK_LIBRARY_DATA = {dump_json(payload)};\n"
