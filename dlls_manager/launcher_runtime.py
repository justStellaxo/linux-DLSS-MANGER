from __future__ import annotations

import os
import shlex
import subprocess

from dlls_manager.execution.base import build_execution_plan
from dlls_manager.execution.steam import is_steam_backed_install
from dlls_manager.install_db import get_install
from dlls_manager.launch_plan import build_effective_profile, build_install_launch_plan, missing_runtime_tools
from dlls_manager.models import ApplyResult, LaunchResult, PreparedLaunch
from dlls_manager.mutations.base import apply_mutation_plan
from dlls_manager.mutations import rollback_mutation
from dlls_manager.override_db import load_install_override
from dlls_manager.profile_db import load_profile
from dlls_manager.release_support import build_result_summary
from dlls_manager.utils import is_process_running


def prepare_launch(install_id: str, profile_name: str) -> PreparedLaunch:
    install = get_install(install_id)
    base_profile = load_profile(profile_name)
    override = load_install_override(install_id)
    effective_profile = build_effective_profile(base_profile, override)
    launch_plan = build_install_launch_plan(install_id, profile_name)
    execution = build_execution_plan(install)
    return {
        "install": install,
        "profile": profile_name,
        "effective_profile": effective_profile,
        "override": override,
        "launch_plan": launch_plan,
        "mutation_plan": launch_plan["mutation_plan"],
        "execution": execution,
        "release_support": launch_plan["release_support"],
        "summary": build_result_summary(
            install,
            profile_name,
            launch_plan["compatibility_status"],
            list(launch_plan["warnings"]),
            list(launch_plan["blocked_reasons"]),
        ),
    }


def apply_install_plan(install_id: str, profile_name: str, force: bool = False) -> ApplyResult:
    prepared = prepare_launch(install_id, profile_name)
    result = apply_mutation_plan(prepared["mutation_plan"], force=force)
    result["summary"] = build_result_summary(
        prepared["install"],
        profile_name,
        prepared["launch_plan"]["compatibility_status"],
        list(result["warnings"]),
        list(result["errors"]),
    )
    return result


def _final_command(prepared: PreparedLaunch) -> list[str]:
    execution = prepared["execution"]
    if is_steam_backed_install(prepared["install"]):
        args = shlex.split(execution["args"]) if execution["args"] else []
        return [*execution["executable"], *args]

    launch_plan = prepared["launch_plan"]
    args = shlex.split(launch_plan["args"]) if launch_plan["args"] else []
    return [*launch_plan["wrappers"], *execution["executable"], *args]


def _steam_is_running() -> bool:
    return is_process_running({"steam"})


def _steam_sync_active(prepared: PreparedLaunch) -> bool:
    return any(step["id"].startswith("sync-steam-") for step in prepared["mutation_plan"]["steps"])


def _rollback_after_launch_failure(
    applied: ApplyResult | None,
    warnings: list[str],
    errors: list[str],
    success_warning: str = "Launch failed after applying mutations; automatic rollback restored the modified files.",
) -> tuple[list[str], list[str]]:
    if not applied or not applied.get("rollback_id"):
        return warnings, errors

    rollback = rollback_mutation(str(applied["rollback_id"]))
    if rollback["ok"]:
        warnings.append(success_warning)
        return warnings, errors

    errors.extend(f"auto-rollback: {message}" for message in rollback["errors"])
    return warnings, errors


def launch_install(
    install_id: str,
    profile_name: str,
    dry_run: bool = False,
    wait: bool = False,
    force: bool = False,
) -> LaunchResult:
    prepared = prepare_launch(install_id, profile_name)
    command = _final_command(prepared)
    warnings = list(prepared["launch_plan"]["warnings"])
    blocked_reasons = list(prepared["launch_plan"]["blocked_reasons"])
    if blocked_reasons and not force:
        return {
            "ok": False,
            "pid": None,
            "returncode": None,
            "command": command,
            "applied": None,
            "errors": blocked_reasons,
            "warnings": warnings,
            "summary": build_result_summary(prepared["install"], profile_name, "blocked", warnings, blocked_reasons),
        }

    unavailable_tools = missing_runtime_tools(prepared["install"], prepared["override"], prepared["launch_plan"]["wrappers"])
    if unavailable_tools and not force:
        errors = [f"Required launch wrapper is unavailable: {tool}" for tool in unavailable_tools]
        return {
            "ok": False,
            "pid": None,
            "returncode": None,
            "command": command,
            "applied": None,
            "errors": errors,
            "warnings": warnings,
            "summary": build_result_summary(
                prepared["install"],
                profile_name,
                prepared["launch_plan"]["compatibility_status"],
                warnings,
                errors,
            ),
        }

    applied: ApplyResult | None = None
    if not dry_run:
        applied = apply_mutation_plan(prepared["mutation_plan"], force=force)
        if not applied["ok"]:
            return {
                "ok": False,
                "pid": None,
                "returncode": None,
                "command": command,
                "applied": applied,
                "errors": list(applied["errors"]),
                "warnings": warnings,
                "summary": build_result_summary(
                    prepared["install"],
                    profile_name,
                    prepared["launch_plan"]["compatibility_status"],
                    warnings,
                    list(applied["errors"]),
                ),
            }

    env = os.environ.copy()
    if is_steam_backed_install(prepared["install"]):
        env.update(prepared["execution"]["env"])
    else:
        env.update(prepared["launch_plan"]["env"])
    working_directory = prepared["execution"]["working_directory"] or None

    if dry_run:
        return {
            "ok": True,
            "pid": None,
            "returncode": None,
            "command": command,
            "applied": applied,
            "errors": [],
            "warnings": warnings,
            "summary": build_result_summary(
                prepared["install"],
                profile_name,
                prepared["launch_plan"]["compatibility_status"],
                warnings,
                [],
                ),
            }

    if _steam_sync_active(prepared) and _steam_is_running():
        warnings.append(
            "Steam launcher sync was applied, but automatic launch was skipped because Steam is already running and may not reload localconfig.vdf until restart. Restart Steam and launch the game from the Steam client."
        )
        return {
            "ok": True,
            "pid": None,
            "returncode": None,
            "command": command,
            "applied": applied,
            "errors": [],
            "warnings": warnings,
            "summary": build_result_summary(
                prepared["install"],
                profile_name,
                prepared["launch_plan"]["compatibility_status"],
                warnings,
                [],
            ),
        }

    if wait:
        try:
            completed = subprocess.run(command, cwd=working_directory, env=env, capture_output=True, text=True, check=False)
        except Exception as exc:
            warnings, rollback_errors = _rollback_after_launch_failure(applied, warnings, [])
            return {
                "ok": False,
                "pid": None,
                "returncode": None,
                "command": command,
                "applied": applied,
                "errors": [f"Launch failed to start: {exc}", *rollback_errors],
                "warnings": warnings,
                "summary": build_result_summary(
                    prepared["install"],
                    profile_name,
                    prepared["launch_plan"]["compatibility_status"],
                    warnings,
                    [f"Launch failed to start: {exc}", *rollback_errors],
                ),
            }
        if completed.stdout:
            warnings.append(completed.stdout.strip())
        if completed.stderr:
            warnings.append(completed.stderr.strip())
        exit_errors = [] if completed.returncode == 0 else [f"Launch exited with status {completed.returncode}"]
        if completed.returncode != 0:
            warnings, exit_errors = _rollback_after_launch_failure(
                applied,
                warnings,
                exit_errors,
                success_warning="Launch exited with a non-zero status after applying mutations; automatic rollback restored the modified files.",
            )
        return {
            "ok": completed.returncode == 0,
            "pid": None,
            "returncode": completed.returncode,
            "command": command,
            "applied": applied,
            "errors": exit_errors,
            "warnings": warnings,
            "summary": build_result_summary(
                prepared["install"],
                profile_name,
                prepared["launch_plan"]["compatibility_status"],
                warnings,
                exit_errors,
            ),
        }

    try:
        process = subprocess.Popen(command, cwd=working_directory, env=env)
    except Exception as exc:
        warnings, rollback_errors = _rollback_after_launch_failure(applied, warnings, [])
        return {
            "ok": False,
            "pid": None,
            "returncode": None,
            "command": command,
            "applied": applied,
            "errors": [f"Launch failed to start: {exc}", *rollback_errors],
            "warnings": warnings,
            "summary": build_result_summary(
                prepared["install"],
                profile_name,
                prepared["launch_plan"]["compatibility_status"],
                warnings,
                [f"Launch failed to start: {exc}", *rollback_errors],
            ),
        }
    return {
        "ok": True,
        "pid": process.pid,
        "returncode": None,
        "command": command,
        "applied": applied,
        "errors": [],
        "warnings": warnings,
        "summary": build_result_summary(
            prepared["install"],
            profile_name,
            prepared["launch_plan"]["compatibility_status"],
            warnings,
            [],
        ),
    }
