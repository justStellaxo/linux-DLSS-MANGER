from dlls_manager.models import LauncherInstallRecord


def build_steam_execution(install: LauncherInstallRecord) -> tuple[list[str], list[str]]:
    if install.get("app_id"):
        return ["steam", "-applaunch", str(install["app_id"])], list(install.get("wrapper_chain", []))
    return list(install.get("launch_command", [])), list(install.get("wrapper_chain", []))
