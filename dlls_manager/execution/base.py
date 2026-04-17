from __future__ import annotations

import shlex

from dlls_manager.execution.bottles import build_bottles_execution
from dlls_manager.execution.desktop_exec import build_desktop_execution
from dlls_manager.execution.heroic import build_heroic_execution
from dlls_manager.execution.lutris import build_lutris_execution
from dlls_manager.execution.script_exec import build_script_execution
from dlls_manager.execution.steam import build_steam_execution
from dlls_manager.execution.umu import build_umu_execution
from dlls_manager.models import ExecutionPlan, LauncherInstallRecord


def _command_preview(env: dict[str, str], wrappers: list[str], command: list[str], args: str) -> str:
    parts = [f"{key}={shlex.quote(value)}" for key, value in sorted(env.items())]
    parts.extend(shlex.quote(wrapper) for wrapper in wrappers)
    parts.extend(shlex.quote(part) for part in command)
    if args:
        parts.extend(shlex.quote(arg) for arg in shlex.split(args))
    return " ".join(parts)


def build_execution_plan(install: LauncherInstallRecord) -> ExecutionPlan:
    strategy = install["execution_strategy"]
    if strategy in {"steam_app", "steam_shortcut"}:
        executable, wrappers = build_steam_execution(install)
    elif strategy == "umu_game":
        executable, wrappers = build_umu_execution(install)
    elif strategy == "script_exec":
        executable, wrappers = build_script_execution(install)
    elif strategy == "desktop_exec":
        executable, wrappers = build_desktop_execution(install)
    elif strategy == "lutris_game":
        executable, wrappers = build_lutris_execution(install)
    elif strategy == "bottles_program":
        executable, wrappers = build_bottles_execution(install)
    elif strategy in {"heroic_game", "legendary_game"}:
        executable, wrappers = build_heroic_execution(install)
    else:
        executable = list(install.get("launch_command", []))
        wrappers = list(install.get("wrapper_chain", []))

    env = dict(install.get("launch_env", {}))
    args = install.get("launch_args", "")
    working_directory = install.get("working_directory")
    return {
        "executable": executable,
        "env": env,
        "wrappers": wrappers,
        "args": args,
        "working_directory": working_directory,
        "command_preview": _command_preview(env, wrappers, executable, args),
    }
