"""Library page — shows installed games and detail panel."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QPlainTextEdit,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

from dlls_manager.gui.workers import JobWorker
from dlls_manager.install_db import load_installs, discover_and_cache_installs
from dlls_manager.launch_plan import list_installs_summary, build_install_launch_plan
from dlls_manager.detector import detect_capabilities
from dlls_manager.dlss_catalog import load_dlss_versions
from dlls_manager.override_db import load_install_override, apply_install_override_updates
from dlls_manager.launcher_runtime import prepare_launch, apply_install_plan, launch_install
from dlls_manager.install_db import validate_install


class LibraryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._installs: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Left: install list
        left = QVBoxLayout()
        search_bar = QLineEdit()
        search_bar.setObjectName("search_bar")
        search_bar.setPlaceholderText("Search installs...")
        search_bar.textChanged.connect(self._filter_installs)
        left.addWidget(search_bar)

        self.install_list = QListWidget()
        self.install_list.setObjectName("install_list")
        self.install_list.currentRowChanged.connect(self._on_select_install)
        left.addWidget(self.install_list)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("refresh_button")
        refresh_btn.clicked.connect(self._run_discovery)
        left.addWidget(refresh_btn)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(350)
        layout.addWidget(left_widget)

        # Right: detail panel
        self.detail_panel = DetailPanel()
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setWidget(self.detail_panel)
        layout.addWidget(detail_scroll, stretch=1)

    def refresh(self) -> None:
        try:
            self._installs = list_installs_summary(refresh=False)
        except Exception:
            self._installs = []
        self._populate_list()

    def _populate_list(self) -> None:
        self.install_list.clear()
        for install in self._installs:
            item = QListWidgetItem(f"{install['name']}\n  {install['launcher_family']} · {install['runtime']}")
            item.setData(Qt.UserRole, install)
            self.install_list.addItem(item)
        if self.install_list.count() > 0:
            self.install_list.setCurrentRow(0)

    def _filter_installs(self, text: str) -> None:
        text_lower = text.lower()
        for i in range(self.install_list.count()):
            item = self.install_list.item(i)
            item.setHidden(text_lower not in item.text().lower())

    def _on_select_install(self, row: int) -> None:
        if row < 0 or row >= self.install_list.count():
            return
        item = self.install_list.item(row)
        install = item.data(Qt.UserRole)
        self.detail_panel.load_install(install)

    def _run_discovery(self) -> None:
        self._worker = JobWorker(discover_and_cache_installs)
        self._worker.finished_job.connect(self._on_discovery_done)
        self._worker.error.connect(lambda e: print(f"Discovery error: {e}"))
        self._worker.start()

    def _on_discovery_done(self, result: Any) -> None:
        self.refresh()


class DetailPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._install: dict | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header
        self.name_label = QLabel("Select an install to inspect")
        self.name_label.setObjectName("detail_name")
        self.name_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        layout.addWidget(self.name_label)

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("detail_meta")
        self.meta_label.setStyleSheet("color: #8f98a0;")
        layout.addWidget(self.meta_label)

        # Status badge
        self.status_label = QLabel("")
        self.status_label.setObjectName("detail_status")
        layout.addWidget(self.status_label)

        # Command preview
        layout.addWidget(QLabel("Command Preview"))
        self.command_preview = QPlainTextEdit()
        self.command_preview.setObjectName("command_preview")
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(80)
        layout.addWidget(self.command_preview)

        # Override editor
        layout.addWidget(QLabel("Override Editor"))
        self.dlss_version_select = QComboBox()
        self.dlss_version_select.setObjectName("dlss_version_select")
        layout.addWidget(self.dlss_version_select)

        self.override_launch_args = QLineEdit()
        self.override_launch_args.setObjectName("override_launch_args")
        self.override_launch_args.setPlaceholderText("Launch args")
        layout.addWidget(self.override_launch_args)

        # Toggles
        toggle_layout = QHBoxLayout()
        self.override_mangohud = QCheckBox("MangoHud")
        self.override_mangohud.setObjectName("override_mangohud")
        self.override_gamemode = QCheckBox("GameMode")
        self.override_gamemode.setObjectName("override_gamemode")
        self.override_nvapi = QCheckBox("NVAPI")
        self.override_nvapi.setObjectName("override_nvapi")
        self.override_sync = QCheckBox("Sync to Launcher")
        self.override_sync.setObjectName("override_sync_launcher")
        toggle_layout.addWidget(self.override_mangohud)
        toggle_layout.addWidget(self.override_gamemode)
        toggle_layout.addWidget(self.override_nvapi)
        toggle_layout.addWidget(self.override_sync)
        toggle_widget = QWidget()
        toggle_widget.setLayout(toggle_layout)
        layout.addWidget(toggle_widget)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.setObjectName("validate_button")
        self.validate_btn.clicked.connect(self._on_validate)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("apply_button")
        self.apply_btn.clicked.connect(self._on_apply)
        self.dry_run_btn = QPushButton("Dry Run")
        self.dry_run_btn.setObjectName("dry_run_button")
        self.dry_run_btn.clicked.connect(self._on_dry_run)
        self.launch_btn = QPushButton("Launch")
        self.launch_btn.setObjectName("launch_button")
        self.launch_btn.clicked.connect(self._on_launch)
        self.save_btn = QPushButton("Save Override")
        self.save_btn.setObjectName("save_override_button")
        self.save_btn.clicked.connect(self._on_save_override)
        btn_layout.addWidget(self.validate_btn)
        btn_layout.addWidget(self.dry_run_btn)
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.launch_btn)
        btn_layout.addWidget(self.save_btn)
        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        layout.addWidget(btn_widget)

        # Action result
        self.action_result = QLabel("")
        self.action_result.setObjectName("action_panel")
        self.action_result.setWordWrap(True)
        layout.addWidget(self.action_result)

        layout.addStretch()

    def load_install(self, install: dict) -> None:
        self._install = install
        self.name_label.setText(install.get("name", "Unknown"))
        self.meta_label.setText(
            f"  {install.get('launcher_family', '?')} · {install.get('runtime', '?')} · "
            f"policy={install.get('anti_cheat_policy', '?')}"
        )
        policy = install.get("anti_cheat_policy", "ok")
        if policy == "blocked":
            self.status_label.setText("BLOCKED")
            self.status_label.setStyleSheet("background-color: #8b3a3a; color: #fff; border-radius: 3px; padding: 2px 8px;")
        elif policy == "warn":
            self.status_label.setText("WARN")
            self.status_label.setStyleSheet("background-color: #8a6914; color: #fff; border-radius: 3px; padding: 2px 8px;")
        else:
            self.status_label.setText("OK")
            self.status_label.setStyleSheet("background-color: #5c7e10; color: #fff; border-radius: 3px; padding: 2px 8px;")

        # Populate DLSS version dropdown
        self.dlss_version_select.clear()
        self.dlss_version_select.addItem("Game Default", "game_default")
        try:
            for entry in load_dlss_versions():
                if entry["id"] != "game_default":
                    self.dlss_version_select.addItem(entry["label"], entry["id"])
        except Exception:
            pass

        # Load override
        try:
            install_id = install.get("id", "")
            if install_id:
                override = load_install_override(install_id)
                self.override_launch_args.setText(override.get("launch_args", ""))
                self.override_mangohud.setChecked(override.get("use_mangohud") or False)
                self.override_gamemode.setChecked(override.get("use_gamemode") or False)
                self.override_nvapi.setChecked(override.get("enable_nvapi") or False)
                self.override_sync.setChecked(override.get("sync_to_launcher") or False)
        except Exception:
            pass

        # Update command preview
        self._update_preview()

    def _update_preview(self) -> None:
        if not self._install:
            return
        try:
            install_id = self._install.get("id", "")
            if install_id:
                plan = build_install_launch_plan(install_id, "default")
                self.command_preview.setPlainText(plan.get("command_preview", ""))
        except Exception as e:
            self.command_preview.setPlainText(f"Error: {e}")

    def _get_install_id(self) -> str:
        return self._install.get("id", "") if self._install else ""

    def _on_validate(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        self.action_result.setText("Validating...")
        self._worker = JobWorker(validate_install, install_id)
        self._worker.finished_job.connect(lambda r: self.action_result.setText(f"Validate: {r.get('ok', '?')}"))
        self._worker.error.connect(lambda e: self.action_result.setText(f"Validate error: {e}"))
        self._worker.start()

    def _on_apply(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        self._save_override()
        self.action_result.setText("Applying...")
        self._worker = JobWorker(apply_install_plan, install_id, "default")
        self._worker.finished_job.connect(lambda r: self.action_result.setText(
            f"Apply: ok={r.get('ok')} steps={r.get('applied_steps', [])}"))
        self._worker.error.connect(lambda e: self.action_result.setText(f"Apply error: {e}"))
        self._worker.start()

    def _on_dry_run(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        self._save_override()
        self.action_result.setText("Dry running...")
        self._worker = JobWorker(launch_install, install_id, "default", dry_run=True)
        self._worker.finished_job.connect(lambda r: self.action_result.setText(
            f"Dry Run: ok={r.get('ok')} cmd={' '.join(r.get('command', []))}"))
        self._worker.error.connect(lambda e: self.action_result.setText(f"Dry Run error: {e}"))
        self._worker.start()

    def _on_launch(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        self._save_override()
        self.action_result.setText("Launching...")
        self._worker = JobWorker(launch_install, install_id, "default", dry_run=False, wait=False)
        self._worker.finished_job.connect(lambda r: self.action_result.setText(
            f"Launch: ok={r.get('ok')} pid={r.get('pid')}"))
        self._worker.error.connect(lambda e: self.action_result.setText(f"Launch error: {e}"))
        self._worker.start()

    def _save_override(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        dlss_ver = self.dlss_version_select.currentData()
        if dlss_ver == "game_default":
            dlss_ver = None
        updates = {
            "dlss_version": dlss_ver,
            "launch_args": self.override_launch_args.text(),
            "use_mangohud": self.override_mangohud.isChecked() if self.override_mangohud.isChecked() else None,
            "use_gamemode": self.override_gamemode.isChecked() if self.override_gamemode.isChecked() else None,
            "enable_nvapi": self.override_nvapi.isChecked() if self.override_nvapi.isChecked() else None,
            "sync_to_launcher": self.override_sync.isChecked(),
        }
        try:
            apply_install_override_updates(install_id, updates)
        except Exception as e:
            self.action_result.setText(f"Save override error: {e}")

    def _on_save_override(self) -> None:
        self._save_override()
        self.action_result.setText("Override saved.")
        self._update_preview()