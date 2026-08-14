from dlls_manager.models import LauncherInstallRecord


def is_steam_backed_install(install: LauncherInstallRecord) -> bool:
    return install["source"] == "steam" or (
        install.get("launcher_family") == "steam" and bool(install.get("app_id"))
    )


def build_steam_execution(install: LauncherInstallRecord) -> tuple[list[str], list[str]]:
    if install.get("app_id"):
        return ["steam", "-applaunch", str(install["app_id"])], list(install.get("wrapper_chain", []))
    return list(install.get("launch_command", [])), list(install.get("wrapper_chain", []))
