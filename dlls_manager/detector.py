import platform
import shutil

from dlls_manager.utils import run_cmd


def detect_capabilities() -> dict:
    report = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "nvidia_smi_path": shutil.which("nvidia-smi"),
        "vulkaninfo_path": shutil.which("vulkaninfo"),
        "steam_path": shutil.which("steam"),
    }

    if report["nvidia_smi_path"]:
        report["nvidia_smi"] = run_cmd(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"]
        )
    else:
        report["nvidia_smi"] = "nvidia-smi not found"

    if report["vulkaninfo_path"]:
        report["vulkaninfo_summary"] = run_cmd(["vulkaninfo", "--summary"])
    else:
        report["vulkaninfo_summary"] = "vulkaninfo not found"

    report["steam_available"] = bool(report["steam_path"])
    report["vulkan_available"] = bool(report["vulkaninfo_path"])
    report["nvidia_driver_present"] = bool(report["nvidia_smi_path"])
    report["smooth_motion_supported"] = bool(report["vulkaninfo_path"] and report["nvidia_smi_path"])
    return report
