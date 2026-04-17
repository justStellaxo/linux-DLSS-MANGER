from pathlib import Path

from dlls_manager.models import LauncherInstallRecord


def build_script_execution(install: LauncherInstallRecord) -> tuple[list[str], list[str]]:
    script_path = install.get("script_path")
    if script_path:
        return [str(Path(script_path).expanduser())], list(install.get("wrapper_chain", []))
    return list(install.get("launch_command", [])), list(install.get("wrapper_chain", []))
