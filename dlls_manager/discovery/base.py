from __future__ import annotations

import shlex
from collections.abc import Callable
from pathlib import Path

from dlls_manager.models import DiscoveryReport, LauncherInstallRecord
from dlls_manager.paths import LOCAL_APPLICATIONS_DIR
from dlls_manager.utils import utc_timestamp


def normalize_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return str(Path(path).expanduser())


def build_install_id(source: str, source_id: str) -> str:
    return f"{source}:{source_id}"


def parse_env_assignments(raw: str) -> tuple[dict[str, str], list[str]]:
    env: dict[str, str] = {}
    remainder: list[str] = []
    for token in shlex.split(raw):
        if "=" in token and token.split("=", 1)[0].replace("_", "").isalnum():
            key, value = token.split("=", 1)
            env[key] = value
        else:
            remainder.append(token)
    return env, remainder


def parse_exec_command(raw: str) -> tuple[list[str], list[str]]:
    tokens = shlex.split(raw)
    wrappers: list[str] = []
    command: list[str] = []
    if not tokens:
        return wrappers, command

    index = 0
    while index < len(tokens):
        token = tokens[index]
        token_name = Path(token).name
        if token_name in {"mullvad-exclude", "gamemoderun", "mangohud", "gamescope"}:
            wrappers.append(token_name)
            index += 1
            continue
        command = tokens[index:]
        break
    return wrappers, command


def parse_desktop_entry(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def parse_simple_yaml(path: Path) -> dict[str, object]:
    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(0, root)]

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if ":" not in stripped:
            continue

        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        container = stack[-1][1]

        if not value:
            child: dict[str, object] = {}
            container[key] = child
            stack.append((indent + 2, child))
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        container[key] = value

    return root


def find_matching_desktop_entry(*patterns: str) -> tuple[Path | None, dict[str, str] | None]:
    if not LOCAL_APPLICATIONS_DIR.exists():
        return None, None

    normalized_patterns = [pattern for pattern in patterns if pattern]
    for desktop_path in sorted(LOCAL_APPLICATIONS_DIR.glob("*.desktop")):
        data = parse_desktop_entry(desktop_path)
        haystacks = [
            data.get("Name", ""),
            data.get("Exec", ""),
            data.get("Comment", ""),
            str(desktop_path),
        ]
        if any(pattern in haystack for pattern in normalized_patterns for haystack in haystacks):
            return desktop_path, data
    return None, None


def validate_install_record(install: LauncherInstallRecord) -> LauncherInstallRecord:
    errors: list[str] = []
    warnings = list(install.get("validation_warnings", []))

    def require_existing(path_key: str, level: str = "error") -> None:
        path = install.get(path_key)
        if not path:
            return
        if not Path(path).expanduser().exists():
            message = f"{path_key} does not exist: {path}"
            if level == "error":
                errors.append(message)
            else:
                warnings.append(message)

    require_existing("install_root", level="warning")
    require_existing("prefix_path", level="warning")
    require_existing("exe_path")
    require_existing("script_path")
    require_existing("desktop_file", level="warning")
    require_existing("runner_path", level="warning")
    if install.get("working_directory") and not Path(str(install["working_directory"])).expanduser().exists():
        warnings.append(f"working_directory does not exist: {install['working_directory']}")

    launch_command = install.get("launch_command", [])
    if launch_command:
        executable = Path(launch_command[0]).expanduser()
        if "/" in launch_command[0] and not executable.exists():
            errors.append(f"launch executable does not exist: {launch_command[0]}")
    else:
        warnings.append("No launch command has been recorded for this installation.")

    scan_paths = []
    for path in install.get("scan_paths", []):
        normalized = normalize_path(path)
        if normalized and normalized not in scan_paths:
            scan_paths.append(normalized)

    validated = dict(install)
    validated["validation_errors"] = errors
    validated["validation_warnings"] = warnings
    validated["scan_paths"] = scan_paths
    return validated  # type: ignore[return-value]


def dedupe_installations(installs: list[LauncherInstallRecord]) -> list[LauncherInstallRecord]:
    seen: set[tuple[str | None, str | None, tuple[str, ...]]] = set()
    deduped: list[LauncherInstallRecord] = []
    for install in installs:
        signature = (
            install.get("exe_path"),
            install.get("script_path"),
            tuple(install.get("launch_command", [])),
        )
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(install)
    return deduped


def discover_all_installations() -> DiscoveryReport:
    from dlls_manager.discovery.bottles import discover_bottles_installations
    from dlls_manager.discovery.desktop_entries import discover_desktop_entry_installations
    from dlls_manager.discovery.faugus import discover_faugus_installations
    from dlls_manager.discovery.heroic import discover_heroic_installations
    from dlls_manager.discovery.lutris import discover_lutris_installations
    from dlls_manager.discovery.starcitizen_lug import discover_starcitizen_lug_installations
    from dlls_manager.discovery.steam import discover_steam_installations

    collectors: list[Callable[[], list[LauncherInstallRecord]]] = [
        discover_steam_installations,
        discover_faugus_installations,
        discover_starcitizen_lug_installations,
        discover_heroic_installations,
        discover_lutris_installations,
        discover_bottles_installations,
        discover_desktop_entry_installations,
    ]

    installs: list[LauncherInstallRecord] = []
    warnings: list[str] = []
    for collector in collectors:
        try:
            installs.extend(collector())
        except Exception as exc:
            warnings.append(f"{collector.__name__} failed: {exc}")

    deduped = [validate_install_record(install) for install in dedupe_installations(installs)]
    return {
        "created_at": utc_timestamp(),
        "installs": deduped,
        "warnings": warnings,
    }
