import json
import os
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path):
    """Temporarily redirect all DLLS_Manager paths to tmp_path."""
    root = tmp_path / "project"
    root.mkdir()
    env = {
        "DLLS_MANAGER_PROFILES_DIR": str(root / "profiles"),
        "DLLS_MANAGER_INSTALL_OVERRIDES_DIR": str(root / "overrides"),
        "DLLS_MANAGER_ROLLBACKS_DIR": str(root / "rollbacks"),
        "DLLS_MANAGER_DLSS_RUNTIME_DIR": str(root / "dlss_runtime"),
        "DLLS_MANAGER_DLSS_DOWNLOADS_DIR": str(root / "dlss_downloads"),
        "DLLS_MANAGER_SNAPSHOTS_DIR": str(root / "snapshots"),
        "DLLS_MANAGER_INSTALLS_FILE": str(root / "installs.json"),
        "DLLS_MANAGER_DLSS_VERSIONS_FILE": str(root / "dlss_versions.json"),
        "DLLS_MANAGER_GAMES_FILE": str(root / "games.json"),
        "DLLS_MANAGER_ANTI_CHEAT_RULES_FILE": str(root / "anti_cheat_rules.json"),
    }
    old_env = dict(os.environ)
    os.environ.update(env)
    (root / "profiles").mkdir()
    yield root
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def dlss_zip_with_three_dlls(tmp_path):
    """Create a ZIP containing nvngx_dlss.dll, nvngx_dlssd.dll, nvngx_dlssg.dll."""
    zip_path = tmp_path / "test_dlss.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("sdk/bin/nvngx_dlss.dll", b"sr-dll-bytes")
        archive.writestr("sdk/bin/nvngx_dlssd.dll", b"rr-dll-bytes")
        archive.writestr("sdk/bin/nvngx_dlssg.dll", b"fg-dll-bytes")
    return zip_path


@pytest.fixture
def default_profile(tmp_project):
    """Create a default profile in tmp_project."""
    from dlls_manager.profile_db import save_profile
    save_profile("default", {
        "enable_nvapi": True, "enable_smooth_motion": False,
        "use_gamemode": True, "use_mangohud": False,
        "launch_args": "", "custom_env": {},
        "dlss_mode": "game_default", "dlss_version": None,
        "allow_unsupported_override": False, "safety_mode": "strict",
    })
    return "default"