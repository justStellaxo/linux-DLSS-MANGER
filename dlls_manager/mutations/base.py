from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from dlls_manager.dlss_mutations import resolve_dlss_runtime_path, resolve_dlss_target_path
from dlls_manager.launcher_persistence import build_launcher_sync_steps
from dlls_manager.models import ApplyResult, InstallOverride, LauncherInstallRecord, MutationPlan, MutationStep, RollbackFileRecord, RollbackRecord
from dlls_manager.paths import ROLLBACKS_DIR
from dlls_manager.utils import atomic_write_json, atomic_write_text, ensure_directory, utc_timestamp


def _rollback_id(install_id: str) -> str:
    digest = hashlib.sha1(f"{install_id}:{utc_timestamp()}".encode("utf-8")).hexdigest()[:12]
    return f"rb-{digest}"


def build_mutation_plan(
    install: LauncherInstallRecord,
    profile_name: str,
    override: InstallOverride,
    effective_env: dict[str, str],
    effective_wrappers: list[str],
    launch_args: str,
    compatibility_status: str,
    warnings: list[str],
    blocked_reasons: list[str],
) -> MutationPlan:
    steps: list[MutationStep] = []
    plan_warnings = list(warnings)
    plan_blocked = list(blocked_reasons)

    selected_dlss = override.get("dlss_version") or effective_env.get("DLLS_MANAGER_DLSS_VERSION")
    if selected_dlss and selected_dlss != "game_default":
        runtime_path = resolve_dlss_runtime_path(selected_dlss)
        target_path = resolve_dlss_target_path(install, override)
        if not runtime_path:
            plan_blocked.append(f"DLSS runtime payload for version '{selected_dlss}' is not available in dlss_runtime/.")
        if not target_path:
            plan_blocked.append(f"Could not resolve DLSS target path for install '{install['display_name']}'.")
        if runtime_path and target_path:
            steps.append(
                {
                    "id": f"dlss-{selected_dlss}",
                    "action": "copy_file",
                    "description": f"Swap DLSS runtime to version {selected_dlss}.",
                    "source_path": runtime_path,
                    "target_path": target_path,
                    "payload": None,
                    "backup_required": True,
                }
            )

    if override.get("sync_to_launcher"):
        launcher_steps, launcher_warnings, launcher_blocked = build_launcher_sync_steps(
            install,
            profile_name,
            override,
            effective_env,
            effective_wrappers,
            launch_args,
        )
        steps.extend(launcher_steps)
        plan_warnings.extend(launcher_warnings)
        plan_blocked.extend(launcher_blocked)

    status = "blocked" if plan_blocked else compatibility_status
    return {
        "install_id": install["id"],
        "profile": profile_name,
        "override": override,
        "created_at": utc_timestamp(),
        "status": status,
        "steps": steps,
        "warnings": plan_warnings,
        "blocked_reasons": plan_blocked,
        "compatibility_status": status,
    }


def _rollback_dir(rollback_id: str) -> Path:
    return ensure_directory(ROLLBACKS_DIR / rollback_id)


def _backup_path(rollback_dir: Path, index: int, target: Path) -> Path:
    return rollback_dir / f"{index:03d}-{target.name}.bak"


def _restore_file_record(file_record: RollbackFileRecord) -> tuple[str | None, str | None, str | None]:
    target = Path(file_record["target_path"]).expanduser()
    backup_path = Path(file_record["backup_path"]).expanduser() if file_record["backup_path"] else None

    if file_record["existed_before"]:
        if backup_path is None or not backup_path.exists():
            return None, None, f"{target}: no backup is available for rollback."
        target.parent.mkdir(parents=True, exist_ok=True)
        if backup_path.is_dir():
            if target.exists():
                if target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
            shutil.copytree(backup_path, target)
        else:
            if target.exists() and target.is_dir():
                shutil.rmtree(target)
            shutil.copy2(backup_path, target)
        return str(target), None, None

    if not target.exists():
        return None, None, None

    if target.is_file():
        target.unlink()
    else:
        shutil.rmtree(target)
    return None, str(target), None


def _rollback_file_records(file_records: list[RollbackFileRecord]) -> tuple[list[str], list[str], list[str]]:
    restored: list[str] = []
    removed: list[str] = []
    errors: list[str] = []

    for file_record in reversed(file_records):
        try:
            restored_target, removed_target, error = _restore_file_record(file_record)
            if restored_target:
                restored.append(restored_target)
            if removed_target:
                removed.append(removed_target)
            if error:
                errors.append(error)
        except Exception as exc:
            errors.append(f"{file_record['target_path']}: {exc}")

    return restored, removed, errors


def apply_mutation_plan(plan: MutationPlan, force: bool = False) -> ApplyResult:
    if plan["blocked_reasons"] and not force:
        return {
            "ok": False,
            "rollback_id": None,
            "applied_steps": [],
            "errors": list(plan["blocked_reasons"]),
            "warnings": list(plan["warnings"]),
            "summary": None,
            "plan": plan,
        }

    rollback_id = _rollback_id(plan["install_id"])
    rollback_dir = _rollback_dir(rollback_id)
    file_records: list[RollbackFileRecord] = []
    applied_steps: list[str] = []
    errors: list[str] = []
    warnings = list(plan["warnings"])

    for index, step in enumerate(plan["steps"], start=1):
        target = Path(step["target_path"]).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        existed_before = target.exists()
        backup_path = None
        if step.get("backup_required"):
            backup_candidate = _backup_path(rollback_dir, index, target)
            if existed_before:
                if target.is_file():
                    shutil.copy2(target, backup_candidate)
                else:
                    shutil.copytree(target, backup_candidate)
                backup_path = str(backup_candidate)

        try:
            if step["action"] == "copy_file":
                source = Path(str(step["source_path"])).expanduser()
                shutil.copy2(source, target)
            elif step["action"] == "write_json":
                atomic_write_json(target, step["payload"])
            elif step["action"] == "write_text":
                atomic_write_text(target, str(step["payload"] or ""))
            else:
                raise ValueError(f"Unsupported mutation action: {step['action']}")
            applied_steps.append(step["id"])
            file_records.append(
                {
                    "target_path": str(target),
                    "backup_path": backup_path,
                    "existed_before": existed_before,
                    "action": step["action"],
                }
            )
        except Exception as exc:
            errors.append(f"{step['id']}: {exc}")
            break

    rollback_result: dict[str, object] | None = None
    if errors and file_records:
        restored, removed, rollback_errors = _rollback_file_records(file_records)
        rollback_result = {
            "attempted": True,
            "restored": restored,
            "removed": removed,
            "errors": rollback_errors,
        }
        if rollback_errors:
            errors.extend(f"auto-rollback: {message}" for message in rollback_errors)
        else:
            warnings.append(
                "Mutation apply failed after partial changes; automatic rollback restored the previously modified paths."
            )

    manifest: RollbackRecord = {
        "rollback_id": rollback_id,
        "install_id": plan["install_id"],
        "profile": plan["profile"],
        "created_at": utc_timestamp(),
        "files": file_records,
        "launcher_sync_paths": [step["target_path"] for step in plan["steps"] if step["action"] in {"write_json", "write_text"}],
        "metadata": {
            "plan": plan,
            "applied_steps": applied_steps,
            "apply_errors": errors,
            "auto_rollback": rollback_result,
            "status": "applied" if not errors else "failed_rolled_back" if rollback_result else "failed",
        },
    }
    atomic_write_json(rollback_dir / "manifest.json", manifest)

    ok = not errors
    return {
        "ok": ok,
        "rollback_id": rollback_id if ok else rollback_id,
        "applied_steps": applied_steps,
        "errors": errors,
        "warnings": warnings,
        "summary": None,
        "plan": plan,
    }


def load_rollback_record(rollback_id: str) -> RollbackRecord:
    manifest_path = ROLLBACKS_DIR / rollback_id / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Rollback manifest not found: {manifest_path}")
    payload = Path(manifest_path).read_text(encoding="utf-8")
    import json

    return json.loads(payload)


def list_rollbacks() -> list[dict]:
    if not ROLLBACKS_DIR.exists():
        return []
    entries: list[dict] = []
    for manifest in sorted(ROLLBACKS_DIR.glob("*/manifest.json")):
        record = load_rollback_record(manifest.parent.name)
        entries.append(
            {
                "rollback_id": record["rollback_id"],
                "install_id": record["install_id"],
                "profile": record["profile"],
                "created_at": record["created_at"],
                "files": len(record["files"]),
            }
        )
    return entries


def rollback_mutation(rollback_id: str) -> dict:
    record = load_rollback_record(rollback_id)
    restored, removed, errors = _rollback_file_records(record["files"])

    return {
        "ok": not errors,
        "rollback_id": rollback_id,
        "restored": restored,
        "removed": removed,
        "errors": errors,
    }
