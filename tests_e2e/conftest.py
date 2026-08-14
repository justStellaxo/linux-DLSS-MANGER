import json
import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QListWidget, QTableWidget, QLineEdit, QCheckBox, QComboBox


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# NOTE: do NOT define qtbot here — pytest-qt provides it automatically
# when qt_api=pyside6 is set in pytest.ini


@pytest.fixture
def gui_env(tmp_path, monkeypatch):
    """Full isolated environment for GUI tests — all paths redirected."""
    root = tmp_path / "gui-test"
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
    for key, val in env.items():
        monkeypatch.setenv(key, val)

    # Patch module-level path constants that were bound at import time
    from dlls_manager import paths as _paths
    from dlls_manager import install_db as _install_db
    from dlls_manager import override_db as _override_db
    from dlls_manager import dlss_catalog as _dlss_catalog
    from dlls_manager import profile_db as _profile_db
    from dlls_manager import launch_plan as _launch_plan
    from dlls_manager import snapshots as _snapshots
    from dlls_manager import anti_cheat as _anti_cheat
    from dlls_manager import game_db as _game_db
    from dlls_manager import dlss_mutations as _dlss_mutations
    from dlls_manager.mutations import base as _mutations_base

    monkeypatch.setattr(_paths, "PROFILES_DIR", root / "profiles")
    monkeypatch.setattr(_paths, "INSTALL_OVERRIDES_DIR", root / "overrides")
    monkeypatch.setattr(_paths, "ROLLBACKS_DIR", root / "rollbacks")
    monkeypatch.setattr(_paths, "DLSS_RUNTIME_DIR", root / "dlss_runtime")
    monkeypatch.setattr(_paths, "DLSS_DOWNLOADS_DIR", root / "dlss_downloads")
    monkeypatch.setattr(_paths, "SNAPSHOTS_DIR", root / "snapshots")
    monkeypatch.setattr(_paths, "INSTALLS_FILE", root / "installs.json")
    monkeypatch.setattr(_paths, "DLSS_VERSIONS_FILE", root / "dlss_versions.json")
    monkeypatch.setattr(_paths, "GAMES_FILE", root / "games.json")
    monkeypatch.setattr(_paths, "ANTI_CHEAT_RULES_FILE", root / "anti_cheat_rules.json")

    # Patch consumers that imported path constants at module level
    monkeypatch.setattr(_install_db, "INSTALLS_FILE", root / "installs.json")
    monkeypatch.setattr(_override_db, "INSTALL_OVERRIDES_DIR", root / "overrides")
    monkeypatch.setattr(_dlss_catalog, "DLSS_VERSIONS_FILE", root / "dlss_versions.json")
    monkeypatch.setattr(_dlss_catalog, "DLSS_RUNTIME_DIR", root / "dlss_runtime")
    monkeypatch.setattr(_dlss_catalog, "DLSS_DOWNLOADS_DIR", root / "dlss_downloads")
    monkeypatch.setattr(_profile_db, "PROFILES_DIR", root / "profiles")
    monkeypatch.setattr(_snapshots, "SNAPSHOTS_DIR", root / "snapshots")
    monkeypatch.setattr(_anti_cheat, "ANTI_CHEAT_RULES_FILE", root / "anti_cheat_rules.json")
    monkeypatch.setattr(_game_db, "GAMES_FILE", root / "games.json")
    monkeypatch.setattr(_dlss_mutations, "DLSS_RUNTIME_DIR", root / "dlss_runtime")
    monkeypatch.setattr(_mutations_base, "ROLLBACKS_DIR", root / "rollbacks")

    (root / "profiles").mkdir()
    yield root


@pytest.fixture
def gui_with_installs(gui_env):
    """GUI env with 2 sample installs (ok, blocked) and DLSS catalog."""
    from dlls_manager.profile_db import save_profile

    save_profile("default", {
        "enable_nvapi": False, "enable_smooth_motion": False,
        "use_gamemode": False, "use_mangohud": False,
        "launch_args": "", "custom_env": {},
        "dlss_mode": "game_default", "dlss_version": None,
        "allow_unsupported_override": False, "safety_mode": "strict",
        "dlss_sr_preset": None, "dlss_rr_preset": None,
        "dlss_fg_override": None, "enable_ngx_updater": False,
        "enable_hags": False, "enable_vkreflex": False,
        "proton_dlss_upgrade": None,
    })

    installs = {
        "created_at": "2026-01-01T00:00:00Z",
        "warnings": [],
        "installs": [
            {
                "id": "manual:test-game",
                "display_name": "Test Game",
                "source": "manual", "source_id": "test-game",
                "launcher_family": "manual", "store_family": "generic",
                "execution_strategy": "script_exec", "runtime": "wine-script",
                "install_root": str(gui_env / "game"),
                "prefix_path": None, "runner_name": None, "runner_path": None,
                "exe_path": None, "script_path": str(gui_env / "game" / "run.sh"),
                "desktop_file": None, "app_id": None,
                "launch_command": [str(gui_env / "game" / "run.sh")],
                "launch_env": {}, "launch_args": "", "wrapper_chain": [],
                "working_directory": str(gui_env / "game"),
                "scan_paths": [], "notes": [],
                "validation_errors": [], "validation_warnings": [],
                "discovery_confidence": "high",
                "anti_cheat": "none", "anti_cheat_vendor": None,
                "anti_cheat_policy": "verified_supported",
                "supports_dlss_override": True,
                "supports_dlss_version_selection": True,
                "override_mode": "experimental",
            },
            {
                "id": "manual:blocked-game",
                "display_name": "Blocked Game",
                "source": "manual", "source_id": "blocked-game",
                "launcher_family": "manual", "store_family": "generic",
                "execution_strategy": "script_exec", "runtime": "wine-script",
                "install_root": str(gui_env / "blocked"),
                "prefix_path": None, "runner_name": None, "runner_path": None,
                "exe_path": None, "script_path": None,
                "desktop_file": None, "app_id": None,
                "launch_command": [], "launch_env": {},
                "launch_args": "", "wrapper_chain": [],
                "working_directory": None, "scan_paths": [], "notes": [],
                "validation_errors": [], "validation_warnings": [],
                "discovery_confidence": "high",
                "anti_cheat": "high", "anti_cheat_vendor": "EasyAntiCheat",
                "anti_cheat_policy": "blocked",
                "supports_dlss_override": False,
                "supports_dlss_version_selection": False,
                "override_mode": "blocked",
            },
        ],
    }
    (gui_env / "installs.json").write_text(json.dumps(installs))
    (gui_env / "game").mkdir()
    run_script = gui_env / "game" / "run.sh"
    run_script.write_text("#!/usr/bin/env bash\nexit 0\n")
    run_script.chmod(0o755)
    (gui_env / "game" / "nvngx_dlss.dll").write_text("original-dll")

    dlss_versions = [
        {"id": "game_default", "label": "Game Default", "selectable": True, "source": "built_in"},
        {"id": "3.7.20", "version": "3.7.20", "label": "DLSS 3.7.20", "selectable": True,
         "source": "official_nvidia_github", "browser_download_url": "http://invalid/test.zip",
         "asset_name": "test.zip", "asset_size": 100, "asset_content_type": "application/zip",
         "published_at": "2026-01-01T00:00:00Z", "release_name": "Test", "release_url": "http://invalid"},
    ]
    (gui_env / "dlss_versions.json").write_text(json.dumps(dlss_versions))

    runtime_dir = gui_env / "dlss_runtime" / "3.7.20"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "nvngx_dlss.dll").write_text("new-dll")

    return gui_env


def click_button(parent: QWidget, object_name: str) -> None:
    button = parent.findChild(QPushButton, object_name)
    assert button is not None, f"Button '{object_name}' not found"
    button.click()


def get_list_widget_items(parent: QWidget, object_name: str) -> list[str]:
    widget = parent.findChild(QListWidget, object_name)
    assert widget is not None, f"QListWidget '{object_name}' not found"
    return [widget.item(i).text() for i in range(widget.count())]


def select_sidebar_item(main_window: QWidget, index: int) -> None:
    sidebar = main_window.findChild(QListWidget, "sidebar")
    assert sidebar is not None
    sidebar.setCurrentRow(index)


def fill_line_edit(parent: QWidget, object_name: str, text: str) -> None:
    widget = parent.findChild(QLineEdit, object_name)
    assert widget is not None, f"QLineEdit '{object_name}' not found"
    widget.setText(text)


def check_checkbox(parent: QWidget, object_name: str, checked: bool = True) -> None:
    widget = parent.findChild(QCheckBox, object_name)
    assert widget is not None, f"QCheckBox '{object_name}' not found"
    widget.setChecked(checked)


def select_combobox(parent: QWidget, object_name: str, value: str) -> None:
    widget = parent.findChild(QComboBox, object_name)
    assert widget is not None, f"QComboBox '{object_name}' not found"
    idx = widget.findText(value)
    if idx >= 0:
        widget.setCurrentIndex(idx)
    else:
        idx = widget.findData(value)
        if idx >= 0:
            widget.setCurrentIndex(idx)