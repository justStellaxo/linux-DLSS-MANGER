from __future__ import annotations

from pathlib import Path

from dlls_manager.discovery import discover_all_installations
from dlls_manager.models import DiscoveryReport, LauncherInstallRecord, ValidationResult
from dlls_manager.paths import INSTALLS_FILE
from dlls_manager.release_support import build_result_summary, get_release_support
from dlls_manager.utils import dump_json, load_json


def discover_and_cache_installs() -> DiscoveryReport:
    report = discover_all_installations()
    INSTALLS_FILE.write_text(dump_json(report), encoding="utf-8")
    return report


def load_install_report(refresh: bool = False) -> DiscoveryReport:
    if refresh or not INSTALLS_FILE.exists():
        return discover_and_cache_installs()
    payload = load_json(INSTALLS_FILE)
    if not isinstance(payload, dict):
        raise ValueError("installs.json must contain a top-level object.")
    return payload  # type: ignore[return-value]


def load_installs(refresh: bool = False) -> list[LauncherInstallRecord]:
    return load_install_report(refresh)["installs"]


def get_install(install_id: str, refresh: bool = False) -> LauncherInstallRecord:
    installs = {install["id"]: install for install in load_installs(refresh)}
    if install_id not in installs:
        raise KeyError(f"Install ID '{install_id}' not found in installs.json")
    return installs[install_id]


def validate_install(install_id: str, refresh: bool = False) -> ValidationResult:
    install = get_install(install_id, refresh=refresh)
    errors = list(install["validation_errors"])
    warnings = list(install["validation_warnings"])
    release_support = get_release_support(install)
    return {
        "install_id": install_id,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "release_support": release_support,
        "summary": build_result_summary(install, None, "blocked" if errors else "warn" if warnings else "ok", warnings, errors),
    }
