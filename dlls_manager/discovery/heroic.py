from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from dlls_manager.discovery.base import build_install_id, normalize_path
from dlls_manager.models import LauncherInstallRecord, StoreFamily
from dlls_manager.paths import HEROIC_CONFIG_DIRS


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "heroic-game"


def _store_family_for(path: Path, item: dict[str, Any]) -> StoreFamily:
    haystack = " ".join(
        [
            str(path),
            str(item.get("store", "")),
            str(item.get("platform", "")),
            str(item.get("runner", "")),
        ]
    ).lower()
    if "legendary" in haystack or "epic" in haystack:
        return "epic"
    if "gog" in haystack:
        return "gog"
    if "nile" in haystack or "amazon" in haystack:
        return "amazon"
    return "generic"


def _extract_game_objects(payload: Any) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        candidate_keys = {"app_name", "appName", "title", "install_path", "installPath", "winePrefix", "winePrefixPath"}
        if candidate_keys.intersection(payload):
            matches.append(payload)
        for value in payload.values():
            matches.extend(_extract_game_objects(value))
    elif isinstance(payload, list):
        for value in payload:
            matches.extend(_extract_game_objects(value))
    return matches


def _manifest_candidates(root: Path) -> list[Path]:
    patterns = ("**/installed.json", "**/installed*.json", "**/library.json")
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(sorted(root.glob(pattern)))
    seen: set[Path] = set()
    deduped: list[Path] = []
    for candidate in candidates:
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def discover_heroic_installations() -> list[LauncherInstallRecord]:
    installs: list[LauncherInstallRecord] = []
    for root in HEROIC_CONFIG_DIRS:
        if not root.exists():
            continue

        for manifest_path in _manifest_candidates(root):
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue

            for item in _extract_game_objects(payload):
                app_name = str(item.get("app_name") or item.get("appName") or item.get("id") or "").strip()
                title = str(item.get("title") or item.get("name") or app_name).strip()
                install_root = normalize_path(item.get("install_path") or item.get("installPath") or item.get("path"))
                if not title or not install_root:
                    continue

                prefix_path = normalize_path(item.get("winePrefix") or item.get("winePrefixPath"))
                exe_path = normalize_path(item.get("executable") or item.get("exe"))
                runner_name = str(item.get("runner") or item.get("runnerVersion") or item.get("wineVersion") or "").strip() or None
                store_family = _store_family_for(manifest_path, item)
                source_id = _slugify(app_name or title)
                execution_strategy = "legendary_game" if store_family == "epic" else "heroic_game"
                launcher = "heroic"

                installs.append(
                    {
                        "id": build_install_id("heroic", source_id),
                        "display_name": title,
                        "source": "heroic",
                        "source_id": source_id,
                        "launcher_family": launcher,
                        "store_family": store_family,
                        "execution_strategy": execution_strategy,  # type: ignore[typeddict-item]
                        "runtime": f"heroic-{store_family}",
                        "install_root": install_root,
                        "prefix_path": prefix_path,
                        "runner_name": runner_name,
                        "runner_path": None,
                        "exe_path": exe_path,
                        "script_path": None,
                        "desktop_file": None,
                        "app_id": app_name or None,
                        "launch_command": ["heroic", "--launch", app_name or title],
                        "launch_env": {},
                        "launch_args": "",
                        "wrapper_chain": [],
                        "working_directory": install_root,
                        "scan_paths": [path for path in [install_root, prefix_path, exe_path] if path],
                        "notes": [f"Imported from Heroic manifest: {manifest_path}"],
                        "validation_errors": [],
                        "validation_warnings": [],
                        "discovery_confidence": "medium",
                        "anti_cheat": "unknown",
                        "anti_cheat_vendor": None,
                        "anti_cheat_policy": "warn",
                        "supports_dlss_override": False,
                        "supports_dlss_version_selection": False,
                        "override_mode": "experimental",
                    }
                )
    return installs
