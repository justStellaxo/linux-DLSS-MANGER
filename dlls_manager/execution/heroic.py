from dlls_manager.models import LauncherInstallRecord


def build_heroic_execution(install: LauncherInstallRecord) -> tuple[list[str], list[str]]:
    return list(install.get("launch_command", [])), list(install.get("wrapper_chain", []))
