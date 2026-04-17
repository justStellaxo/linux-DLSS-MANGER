import shlex

from dlls_manager.anti_cheat import classify_game, classify_install
from dlls_manager.execution.base import build_execution_plan
from dlls_manager.dlss_policy import evaluate_dlss_policy
from dlls_manager.game_db import get_game, load_games
from dlls_manager.install_db import get_install, load_installs
from dlls_manager.mutations.base import build_mutation_plan
from dlls_manager.models import (
    AntiCheatAssessment,
    DlssPolicyEvaluation,
    ExecutionPlan,
    GameRecord,
    InstallLaunchPlan,
    InstallOverride,
    LaunchPlan,
    LauncherInstallRecord,
    Profile,
)
from dlls_manager.override_db import load_install_override
from dlls_manager.profile_db import load_profile
from dlls_manager.release_support import get_release_support


def requested_features(profile: Profile) -> list[str]:
    features = []
    if profile.get("enable_nvapi"):
        features.append("nvapi_override")
    if profile.get("allow_unsupported_override"):
        features.append("unsupported_override")
    if profile.get("enable_smooth_motion"):
        features.append("smooth_motion")
    if profile.get("dlss_version"):
        features.append("dlss_version_selection")
    return features


def _unique_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def build_command_preview(game: GameRecord, env: dict[str, str], wrappers: list[str], args: str) -> str:
    parts = [f"{key}={shlex.quote(value)}" for key, value in sorted(env.items())]
    parts.extend(shlex.quote(wrapper) for wrapper in wrappers)
    if game["launcher"] == "steam" and "app_id" in game:
        parts.extend(["steam", "-applaunch", shlex.quote(game["app_id"])])
    else:
        parts.append("manual-launch")
        parts.append(shlex.quote(game["id"]))
    if args:
        parts.extend(shlex.quote(arg) for arg in shlex.split(args))
    return " ".join(parts)


def build_execution_preview(execution: ExecutionPlan, extra_env: dict[str, str], extra_wrappers: list[str]) -> str:
    env = {**execution["env"], **extra_env}
    wrappers = [*extra_wrappers, *execution["wrappers"]]
    parts = [f"{key}={shlex.quote(value)}" for key, value in sorted(env.items())]
    parts.extend(shlex.quote(wrapper) for wrapper in wrappers)
    parts.extend(shlex.quote(part) for part in execution["executable"])
    if execution["args"]:
        parts.extend(shlex.quote(arg) for arg in shlex.split(execution["args"]))
    return " ".join(parts)


def merge_launch_args(*parts: str) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def build_effective_profile(base_profile: Profile, override: InstallOverride) -> Profile:
    effective = dict(base_profile)
    effective["custom_env"] = {**base_profile.get("custom_env", {}), **override.get("extra_env", {})}
    if override.get("launch_args"):
        effective["launch_args"] = " ".join(
            part for part in [base_profile.get("launch_args", "").strip(), override["launch_args"].strip()] if part
        )
    for key in (
        "enable_nvapi",
        "enable_smooth_motion",
        "use_gamemode",
        "use_mangohud",
        "allow_unsupported_override",
    ):
        if override.get(key) is not None:
            effective[key] = override[key]
    if override.get("dlss_version") is not None:
        effective["dlss_version"] = override["dlss_version"]
    return effective  # type: ignore[return-value]


def build_profile_env_and_wrappers(profile: Profile, override: InstallOverride | None = None) -> tuple[dict[str, str], list[str]]:
    env: dict[str, str] = {}
    if profile.get("enable_nvapi"):
        env["PROTON_ENABLE_NVAPI"] = "1"
        env["DXVK_ENABLE_NVAPI"] = "1"
    if profile.get("enable_smooth_motion"):
        env["NVPRESENT_ENABLE_SMOOTH_MOTION"] = "1"
    if profile.get("dlss_version"):
        env["DLLS_MANAGER_DLSS_VERSION"] = str(profile["dlss_version"])
    env.update(profile.get("custom_env", {}))

    wrappers = []
    if profile.get("use_gamemode"):
        wrappers.append("gamemoderun")
    if profile.get("use_mangohud"):
        wrappers.append("mangohud")
    if override:
        wrappers.extend(override.get("extra_wrappers", []))
    return env, wrappers


def evaluate_plan(game: GameRecord, profile: Profile) -> dict[str, AntiCheatAssessment | DlssPolicyEvaluation | list[str] | str]:
    anti_cheat = classify_game(game)
    dlss = evaluate_dlss_policy(game, profile)
    features = requested_features(profile)
    warnings = list(dlss["warnings"])
    blocked_reasons = list(dlss["blocked_reasons"])

    if anti_cheat["policy"] == "blocked" and features:
        blocked_reasons.append(
            f"Anti-cheat policy blocks experimental features for this title "
            f"({anti_cheat['vendor'] or 'unknown'}, level={anti_cheat['anti_cheat_level']})."
        )
    elif anti_cheat["policy"] == "warn" and features:
        warnings.append(
            f"Anti-cheat policy requires caution for requested features "
            f"({anti_cheat['vendor'] or 'unknown'}, confidence={anti_cheat['confidence']})."
        )

    if profile.get("enable_nvapi") and not game.get("supports_dlss_override", False):
        warnings.append(f"Game '{game['id']}' is not marked as supporting DLSS/NVAPI override workflows.")

    if "smooth_motion" in features and anti_cheat["policy"] != "verified_supported":
        warnings.append("Smooth Motion on non-verified anti-cheat titles should be treated as high risk.")

    compatibility_status = "blocked" if blocked_reasons else "warn" if warnings else "ok"
    return {
        "anti_cheat": anti_cheat,
        "dlss": dlss,
        "requested_features": features,
        "warnings": warnings,
        "blocked_reasons": blocked_reasons,
        "compatibility_status": compatibility_status,
    }


def _evaluate_install_plan(install: LauncherInstallRecord, profile: Profile) -> dict[str, AntiCheatAssessment | DlssPolicyEvaluation | list[str] | str]:
    anti_cheat = classify_install(install)
    game_like_record: GameRecord = {
        "id": install["id"],
        "name": install["display_name"],
        "launcher": install["launcher_family"],
        "runtime": install["runtime"],
        "anti_cheat": install["anti_cheat"],
        "anti_cheat_vendor": install["anti_cheat_vendor"],
        "anti_cheat_policy": install["anti_cheat_policy"],
        "supports_dlss_override": install["supports_dlss_override"],
        "supports_dlss_version_selection": install["supports_dlss_version_selection"],
        "override_mode": install["override_mode"],
        "notes": list(install["notes"]),
        "scan_path": install["scan_paths"][0] if install["scan_paths"] else None,
    }
    dlss = evaluate_dlss_policy(game_like_record, profile)
    features = requested_features(profile)
    warnings = list(dlss["warnings"])
    blocked_reasons = list(dlss["blocked_reasons"])

    if anti_cheat["policy"] == "blocked" and features:
        blocked_reasons.append(
            f"Anti-cheat policy blocks experimental features for this installation "
            f"({anti_cheat['vendor'] or 'unknown'}, level={anti_cheat['anti_cheat_level']})."
        )
    elif anti_cheat["policy"] == "warn" and features:
        warnings.append(
            f"Anti-cheat policy requires caution for requested features "
            f"({anti_cheat['vendor'] or 'unknown'}, confidence={anti_cheat['confidence']})."
        )

    if profile.get("enable_nvapi") and not install.get("supports_dlss_override", False):
        warnings.append(f"Install '{install['display_name']}' is not marked as supporting DLSS/NVAPI override workflows.")

    if "smooth_motion" in features and anti_cheat["policy"] != "verified_supported":
        warnings.append("Smooth Motion on non-verified anti-cheat titles should be treated as high risk.")

    compatibility_status = "blocked" if blocked_reasons else "warn" if warnings else "ok"
    return {
        "anti_cheat": anti_cheat,
        "dlss": dlss,
        "requested_features": features,
        "warnings": warnings,
        "blocked_reasons": blocked_reasons,
        "compatibility_status": compatibility_status,
    }


def build_launch_plan(game_id: str, profile_name: str) -> LaunchPlan:
    game = get_game(game_id)
    profile = load_profile(profile_name)

    env, wrappers = build_profile_env_and_wrappers(profile)

    evaluation = evaluate_plan(game, profile)
    command_preview = build_command_preview(game, env, wrappers, profile.get("launch_args", ""))

    return {
        "game": game,
        "profile": profile_name,
        "env": env,
        "wrappers": wrappers,
        "args": profile.get("launch_args", ""),
        "command_preview": command_preview,
        "anti_cheat_assessment": {
            "vendor": evaluation["anti_cheat"]["vendor"],
            "level": evaluation["anti_cheat"]["anti_cheat_level"],
            "policy": evaluation["anti_cheat"]["policy"],
            "confidence": evaluation["anti_cheat"]["confidence"],
        },
        "policy_reasons": evaluation["anti_cheat"]["reasons"],
        "marker_hits": evaluation["anti_cheat"]["marker_hits"],
        "dlss_version_selection": evaluation["dlss"]["selected_version"],
        "requested_features": evaluation["requested_features"],
        "compatibility_status": evaluation["compatibility_status"],
        "warnings": evaluation["warnings"],
        "blocked_reasons": evaluation["blocked_reasons"],
        "notes": [
            "Preview-only prototype: no live game mutation or binary swapping is performed.",
            "Use explain-policy for a deeper policy breakdown.",
        ],
    }


def build_install_launch_plan(install_id: str, profile_name: str) -> InstallLaunchPlan:
    install = get_install(install_id)
    base_profile = load_profile(profile_name)
    override = load_install_override(install_id)
    profile = build_effective_profile(base_profile, override)
    release_support = get_release_support(install)

    env, wrappers = build_profile_env_and_wrappers(profile, override)

    execution = build_execution_plan(install)
    effective_args = merge_launch_args(execution.get("args", ""), profile.get("launch_args", ""))
    evaluation = _evaluate_install_plan(install, profile)
    execution_preview_payload = dict(execution)
    execution_preview_payload["args"] = effective_args
    command_preview = build_execution_preview(execution_preview_payload, env, wrappers)
    mutation_plan = build_mutation_plan(
        install,
        profile_name,
        override,
        {**execution["env"], **env},
        [*wrappers, *execution["wrappers"]],
        effective_args,
        str(evaluation["compatibility_status"]),
        [*install["validation_warnings"], *evaluation["warnings"]],
        [*install["validation_errors"], *evaluation["blocked_reasons"]],
    )
    blocked_reasons = _unique_list([*install["validation_errors"], *evaluation["blocked_reasons"], *mutation_plan["blocked_reasons"]])
    warnings = _unique_list([*install["validation_warnings"], *evaluation["warnings"], *mutation_plan["warnings"]])
    compatibility_status = "blocked" if blocked_reasons else "warn" if warnings else "ok"

    return {
        "install": install,
        "profile": profile_name,
        "base_profile_config": base_profile,
        "effective_profile_config": profile,
        "override": override,
        "env": {**execution["env"], **env},
        "wrappers": [*wrappers, *execution["wrappers"]],
        "args": effective_args,
        "command_preview": command_preview,
        "anti_cheat_assessment": {
            "vendor": evaluation["anti_cheat"]["vendor"],
            "level": evaluation["anti_cheat"]["anti_cheat_level"],
            "policy": evaluation["anti_cheat"]["policy"],
            "confidence": evaluation["anti_cheat"]["confidence"],
        },
        "policy_reasons": evaluation["anti_cheat"]["reasons"],
        "marker_hits": evaluation["anti_cheat"]["marker_hits"],
        "dlss_version_selection": evaluation["dlss"]["selected_version"],
        "requested_features": evaluation["requested_features"],
        "compatibility_status": compatibility_status,
        "warnings": warnings,
        "blocked_reasons": blocked_reasons,
        "mutation_plan": mutation_plan,
        "release_support": release_support,
        "notes": [
            f"Imported from discovery source '{install['source']}'.",
            f"Release support level: {release_support['level']}. {release_support['note']}",
            "Prepared plan includes mutation/apply preview and launcher sync steps.",
        ],
    }


def explain_policy(game_id: str, profile_name: str) -> dict:
    game = get_game(game_id)
    profile = load_profile(profile_name)
    evaluation = evaluate_plan(game, profile)
    return {
        "game_id": game_id,
        "profile": profile_name,
        "anti_cheat": evaluation["anti_cheat"],
        "dlss_policy": evaluation["dlss"],
        "requested_features": evaluation["requested_features"],
        "compatibility_status": evaluation["compatibility_status"],
        "warnings": evaluation["warnings"],
        "blocked_reasons": evaluation["blocked_reasons"],
    }


def explain_install_policy(install_id: str, profile_name: str) -> dict:
    install = get_install(install_id)
    base_profile = load_profile(profile_name)
    override = load_install_override(install_id)
    profile = build_effective_profile(base_profile, override)
    evaluation = _evaluate_install_plan(install, profile)
    install_plan = build_install_launch_plan(install_id, profile_name)
    return {
        "install_id": install_id,
        "profile": profile_name,
        "override": override,
        "anti_cheat": evaluation["anti_cheat"],
        "dlss_policy": evaluation["dlss"],
        "requested_features": evaluation["requested_features"],
        "compatibility_status": install_plan["compatibility_status"],
        "warnings": install_plan["warnings"],
        "blocked_reasons": install_plan["blocked_reasons"],
    }


def list_games_summary() -> list[dict]:
    summary = []
    for game in load_games():
        anti_cheat = classify_game(game)
        summary.append(
            {
                "id": game["id"],
                "name": game["name"],
                "launcher": game["launcher"],
                "runtime": game["runtime"],
                "anti_cheat_vendor": anti_cheat["vendor"],
                "anti_cheat_level": anti_cheat["anti_cheat_level"],
                "anti_cheat_policy": anti_cheat["policy"],
                "anti_cheat_confidence": anti_cheat["confidence"],
                "supports_dlss_override": game["supports_dlss_override"],
                "supports_dlss_version_selection": game["supports_dlss_version_selection"],
            }
        )
    return summary


def list_installs_summary(refresh: bool = False) -> list[dict]:
    summary = []
    for install in load_installs(refresh=refresh):
        anti_cheat = classify_install(install)
        release_support = get_release_support(install)
        summary.append(
            {
                "id": install["id"],
                "name": install["display_name"],
                "source": install["source"],
                "launcher_family": install["launcher_family"],
                "store_family": install["store_family"],
                "runtime": install["runtime"],
                "anti_cheat_vendor": anti_cheat["vendor"],
                "anti_cheat_level": anti_cheat["anti_cheat_level"],
                "anti_cheat_policy": anti_cheat["policy"],
                "anti_cheat_confidence": anti_cheat["confidence"],
                "release_support": release_support["level"],
                "validation_errors": install["validation_errors"],
                "validation_warnings": install["validation_warnings"],
            }
        )
    return summary
