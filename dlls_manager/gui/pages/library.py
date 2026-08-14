"""Library page — shows installed games and detail panel."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

from dlls_manager.gui.workers import JobWorker
from dlls_manager.install_db import discover_and_cache_installs
from dlls_manager.launch_plan import list_installs_summary, build_install_launch_plan
from dlls_manager.dlss_catalog import load_dlss_versions
from dlls_manager.override_db import load_install_override, apply_install_override_updates
from dlls_manager.launcher_runtime import apply_install_plan, launch_install
from dlls_manager.install_db import validate_install
from dlls_manager.profile_db import list_profiles


class LibraryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._installs: list[dict] = []
        self._worker: JobWorker | None = None
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

        self.refresh_btn = QPushButton("  🔄  Refresh")
        self.refresh_btn.setObjectName("refresh_button")
        self.refresh_btn.setToolTip("Re-scan all launchers for game installs")
        self.refresh_btn.clicked.connect(self._run_discovery)
        left.addWidget(self.refresh_btn)

        self.empty_label = QLabel("No installs found.\nClick Refresh to scan.")
        self.empty_label.setObjectName("empty_state_label")
        self.empty_label.setStyleSheet("color: #8f98a0; padding: 20px; text-align: center;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        left.addWidget(self.empty_label)

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
            policy = install.get("anti_cheat_policy", "ok")
            icon = {"blocked": "🔴", "warn": "🟡"}.get(policy, "🟢")
            item = QListWidgetItem(f"{icon}  {install['name']}\n  {install['launcher_family']} · {install['runtime']}")
            item.setData(Qt.UserRole, install)
            self.install_list.addItem(item)
        has_installs = self.install_list.count() > 0
        self.empty_label.setVisible(not has_installs)
        self.install_list.setVisible(has_installs)
        if has_installs:
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
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("  🔄  Scanning...")
        self._worker = JobWorker(discover_and_cache_installs)
        self._worker.finished_job.connect(self._on_discovery_done)
        self._worker.error.connect(self._on_discovery_error)
        self._worker.start()

    def _on_discovery_done(self, result: Any) -> None:
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("  🔄  Refresh")
        self.refresh()

    def _on_discovery_error(self, error: str) -> None:
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("  🔄  Refresh")
        QMessageBox.warning(self, "Discovery Error", f"Failed to scan launches:\n{error}")


class DetailPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._install: dict | None = None
        self._worker: JobWorker | None = None
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

        # Release support + validation info
        self.info_label = QLabel("")
        self.info_label.setObjectName("detail_info")
        self.info_label.setStyleSheet("color: #8f98a0; font-size: 13px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Command preview
        layout.addWidget(QLabel("Command Preview"))
        self.command_preview = QPlainTextEdit()
        self.command_preview.setObjectName("command_preview")
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(80)
        layout.addWidget(self.command_preview)

        # Profile selector
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile"))
        self.profile_select = QComboBox()
        self.profile_select.setObjectName("profile_select")
        self.profile_select.currentIndexChanged.connect(self._update_preview)
        profile_row.addWidget(self.profile_select)
        layout.addLayout(profile_row)

        # Override editor
        section = QLabel("Override Editor")
        section.setStyleSheet("font-size: 16px; font-weight: bold; color: #66c0f4;")
        layout.addWidget(section)

        self.dlss_version_select = QComboBox()
        self.dlss_version_select.setObjectName("dlss_version_select")
        self.dlss_version_select.setToolTip("Select a downloaded DLSS version to swap in, or 'Game Default' to keep the shipped version")
        layout.addWidget(QLabel("DLSS Version"))
        layout.addWidget(self.dlss_version_select)

        self.override_launch_args = QLineEdit()
        self.override_launch_args.setObjectName("override_launch_args")
        self.override_launch_args.setPlaceholderText("Launch args")
        self.override_launch_args.textChanged.connect(self._update_preview)
        layout.addWidget(QLabel("Launch Args"))
        layout.addWidget(self.override_launch_args)

        # Extra env
        self.extra_env = QTextEdit()
        self.extra_env.setObjectName("override_extra_env")
        self.extra_env.setPlaceholderText("KEY=value (one per line)")
        self.extra_env.setMaximumHeight(80)
        self.extra_env.setToolTip("Custom environment variables, one KEY=value per line")
        layout.addWidget(QLabel("Extra Env Vars"))
        layout.addWidget(self.extra_env)

        # Toggles — two rows
        toggle_row1 = QHBoxLayout()
        self.override_nvapi = QCheckBox("NVAPI")
        self.override_nvapi.setObjectName("override_nvapi")
        self.override_nvapi.setToolTip("PROTON_ENABLE_NVAPI + DXVK_ENABLE_NVAPI")
        self.override_nvapi.toggled.connect(self._update_preview)
        self.override_smooth_motion = QCheckBox("Smooth Motion")
        self.override_smooth_motion.setObjectName("override_smooth_motion")
        self.override_smooth_motion.setToolTip("NVPRESENT_ENABLE_SMOOTH_MOTION")
        self.override_smooth_motion.toggled.connect(self._update_preview)
        self.override_gamemode = QCheckBox("GameMode")
        self.override_gamemode.setObjectName("override_gamemode")
        self.override_gamemode.setToolTip("gamemoderun wrapper")
        self.override_gamemode.toggled.connect(self._update_preview)
        self.override_mangohud = QCheckBox("MangoHud")
        self.override_mangohud.setObjectName("override_mangohud")
        self.override_mangohud.setToolTip("mangohud overlay wrapper")
        self.override_mangohud.toggled.connect(self._update_preview)
        for cb in (self.override_nvapi, self.override_smooth_motion, self.override_gamemode, self.override_mangohud):
            toggle_row1.addWidget(cb)

        toggle_row2 = QHBoxLayout()
        self.override_hags = QCheckBox("HAGS")
        self.override_hags.setObjectName("override_hags")
        self.override_hags.setToolTip("WINEHAGS=1 — Hardware-accelerated GPU scheduling (needed for Frame Generation)")
        self.override_hags.toggled.connect(self._update_preview)
        self.override_vkreflex = QCheckBox("VKReflex")
        self.override_vkreflex.setObjectName("override_vkreflex")
        self.override_vkreflex.setToolTip("DXVK_NVAPI_VKREFLEX=1 — lower input latency")
        self.override_vkreflex.toggled.connect(self._update_preview)
        self.override_ngx_updater = QCheckBox("NGX Updater")
        self.override_ngx_updater.setObjectName("override_ngx_updater")
        self.override_ngx_updater.setToolTip("PROTON_ENABLE_NGX_UPDATER=1 — auto-update NGX DLLs")
        self.override_ngx_updater.toggled.connect(self._update_preview)
        self.override_sync = QCheckBox("Sync to Launcher")
        self.override_sync.setObjectName("override_sync_launcher")
        self.override_sync.setToolTip("Write launch options into Steam's localconfig.vdf")
        for cb in (self.override_hags, self.override_vkreflex, self.override_ngx_updater, self.override_sync):
            toggle_row2.addWidget(cb)

        toggle_widget = QWidget()
        toggle_layout = QVBoxLayout()
        toggle_layout.addLayout(toggle_row1)
        toggle_layout.addLayout(toggle_row2)
        toggle_widget.setLayout(toggle_layout)
        layout.addWidget(toggle_widget)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.setObjectName("validate_button")
        self.validate_btn.setToolTip("Check install integrity and compatibility")
        self.validate_btn.clicked.connect(self._on_validate)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("apply_button")
        self.apply_btn.setToolTip("Apply DLSS mutations and launch options")
        self.apply_btn.clicked.connect(self._on_apply)
        self.dry_run_btn = QPushButton("Dry Run")
        self.dry_run_btn.setObjectName("dry_run_button")
        self.dry_run_btn.setToolTip("Preview launch without modifying files")
        self.dry_run_btn.clicked.connect(self._on_dry_run)
        self.launch_btn = QPushButton("Launch")
        self.launch_btn.setObjectName("launch_button")
        self.launch_btn.setToolTip("Launch the game with current settings")
        self.launch_btn.clicked.connect(self._on_launch)
        self.save_btn = QPushButton("Save Override")
        self.save_btn.setObjectName("save_override_button")
        self.save_btn.setToolTip("Save per-install override settings")
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
            self.status_label.setText("  🔴  BLOCKED  ")
            self.status_label.setStyleSheet("background-color: #8b3a3a; color: #fff; border-radius: 3px; padding: 2px 8px;")
        elif policy == "warn":
            self.status_label.setText("  🟡  WARN  ")
            self.status_label.setStyleSheet("background-color: #8a6914; color: #fff; border-radius: 3px; padding: 2px 8px;")
        else:
            self.status_label.setText("  🟢  OK  ")
            self.status_label.setStyleSheet("background-color: #5c7e10; color: #fff; border-radius: 3px; padding: 2px 8px;")

        # Show release support + validation info
        parts = []
        if install.get("release_support"):
            parts.append(f"Support: {install['release_support']}")
        if install.get("anti_cheat_vendor"):
            parts.append(f"Anti-cheat: {install['anti_cheat_vendor']}")
        if install.get("validation_errors"):
            parts.append(f"Errors: {', '.join(install['validation_errors'])}")
        if install.get("validation_warnings"):
            parts.append(f"Warnings: {', '.join(install['validation_warnings'])}")
        self.info_label.setText(" · ".join(parts) if parts else "")

        # Populate profile selector
        self.profile_select.clear()
        try:
            for name in list_profiles():
                self.profile_select.addItem(name)
            idx = self.profile_select.findText("default")
            if idx >= 0:
                self.profile_select.setCurrentIndex(idx)
        except Exception:
            pass

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
                self.override_nvapi.setChecked(override.get("enable_nvapi") or False)
                self.override_smooth_motion.setChecked(override.get("enable_smooth_motion") or False)
                self.override_gamemode.setChecked(override.get("use_gamemode") or False)
                self.override_mangohud.setChecked(override.get("use_mangohud") or False)
                self.override_hags.setChecked(override.get("enable_hags") or False)
                self.override_vkreflex.setChecked(override.get("enable_vkreflex") or False)
                self.override_ngx_updater.setChecked(override.get("enable_ngx_updater") or False)
                self.override_sync.setChecked(override.get("sync_to_launcher") or False)
                extra_env = override.get("extra_env", {})
                if isinstance(extra_env, dict):
                    self.extra_env.setPlainText(
                        "\n".join(f"{k}={v}" for k, v in extra_env.items())
                    )
        except Exception:
            pass

        # Update command preview
        self._update_preview()

    def _get_profile(self) -> str:
        return self.profile_select.currentText() or "default"

    def _update_preview(self) -> None:
        if not self._install:
            return
        try:
            install_id = self._install.get("id", "")
            if install_id:
                self._save_override()
                plan = build_install_launch_plan(install_id, self._get_profile())
                self.command_preview.setPlainText(plan.get("command_preview", ""))
        except Exception:
            pass

    def _get_install_id(self) -> str:
        return self._install.get("id", "") if self._install else ""

    def _on_validate(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        self.action_result.setText("Validating...")
        self._worker = JobWorker(validate_install, install_id)
        self._worker.finished_job.connect(lambda r: self.action_result.setText(
            f"Validate: {'OK' if r.get('ok') else 'FAILED'}"
            + (f" — {', '.join(r.get('errors', []))}" if r.get("errors") else "")
        ))
        self._worker.error.connect(lambda e: self.action_result.setText(f"Validate error: {e}"))
        self._worker.start()

    def _on_apply(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        reply = QMessageBox.question(
            self, "Confirm Apply",
            f"Apply DLSS mutations to '{self._install.get('name', '?')}'?\n"
            f"This will modify game files. A rollback snapshot will be created.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._save_override()
        self.action_result.setText("Applying...")
        self._worker = JobWorker(apply_install_plan, install_id, self._get_profile())
        self._worker.finished_job.connect(lambda r: self.action_result.setText(
            f"Apply: {'OK' if r.get('ok') else 'FAILED'} — {len(r.get('applied_steps', []))} steps"
            + (f" (rollback: {r.get('rollback_id', '')})" if r.get("rollback_id") else "")
        ))
        self._worker.error.connect(lambda e: QMessageBox.critical(self, "Apply Error", e))
        self._worker.start()

    def _on_dry_run(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        self._save_override()
        self.action_result.setText("Dry running...")
        self._worker = JobWorker(launch_install, install_id, self._get_profile(), dry_run=True)
        self._worker.finished_job.connect(lambda r: self.action_result.setText(
            f"Dry Run: {'OK' if r.get('ok') else 'FAILED'} — {' '.join(r.get('command', []))}"))
        self._worker.error.connect(lambda e: self.action_result.setText(f"Dry Run error: {e}"))
        self._worker.start()

    def _on_launch(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        reply = QMessageBox.question(
            self, "Confirm Launch",
            f"Launch '{self._install.get('name', '?')}' with profile '{self._get_profile()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._save_override()
        self.action_result.setText("Launching...")
        self._worker = JobWorker(launch_install, install_id, self._get_profile(), dry_run=False, wait=False)
        self._worker.finished_job.connect(lambda r: self.action_result.setText(
            f"Launch: {'OK' if r.get('ok') else 'FAILED'} — PID {r.get('pid')}"))
        self._worker.error.connect(lambda e: QMessageBox.critical(self, "Launch Error", e))
        self._worker.start()

    def _save_override(self) -> None:
        install_id = self._get_install_id()
        if not install_id:
            return
        dlss_ver = self.dlss_version_select.currentData()
        if dlss_ver == "game_default":
            dlss_ver = None
        # Parse extra env
        extra_env: dict[str, str] = {}
        for line in self.extra_env.toPlainText().strip().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                extra_env[k.strip()] = v.strip()
        updates = {
            "dlss_version": dlss_ver,
            "launch_args": self.override_launch_args.text(),
            "enable_nvapi": self.override_nvapi.isChecked() or None,
            "enable_smooth_motion": self.override_smooth_motion.isChecked() or None,
            "use_mangohud": self.override_mangohud.isChecked() or None,
            "use_gamemode": self.override_gamemode.isChecked() or None,
            "enable_hags": self.override_hags.isChecked() or None,
            "enable_vkreflex": self.override_vkreflex.isChecked() or None,
            "enable_ngx_updater": self.override_ngx_updater.isChecked() or None,
            "sync_to_launcher": self.override_sync.isChecked(),
            "extra_env": extra_env if extra_env else None,
        }
        try:
            apply_install_override_updates(install_id, updates)
        except Exception as e:
            self.action_result.setText(f"Save override error: {e}")

    def _on_save_override(self) -> None:
        self._save_override()
        self.action_result.setText("Override saved.")
        self._update_preview()