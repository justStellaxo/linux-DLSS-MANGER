from __future__ import annotations

from pathlib import Path

from dlls_manager.models import InstallOverride, LauncherInstallRecord
from dlls_manager.paths import DLSS_RUNTIME_DIR, PROJECT_ROOT


def resolve_dlss_runtime_path(version_id: str) -> str | None:
    candidates = [
        DLSS_RUNTIME_DIR / version_id / "nvngx_dlss.dll",
        PROJECT_ROOT / "fixtures" / "dlss_versions" / version_id / "nvngx_dlss.dll",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def resolve_dlss_target_path(install: LauncherInstallRecord, override: InstallOverride) -> str | None:
    if override.get("dlss_target_path"):
        return override["dlss_target_path"]

    known_names = ("nvngx_dlss.dll", "nvngx_dlssg.dll")
    search_roots: list[Path] = []
    for path in (install.get("install_root"), install.get("exe_path"), install.get("prefix_path")):
        if not path:
            continue
        candidate = Path(path)
        search_roots.append(candidate.parent if candidate.is_file() else candidate)

    seen: set[str] = set()
    deduped_roots: list[Path] = []
    for root in search_roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        deduped_roots.append(root)

    for root in deduped_roots:
        for name in known_names:
            candidate = root / name
            if candidate.exists():
                return str(candidate)

    if deduped_roots:
        return str(deduped_roots[0] / known_names[0])
    return None
