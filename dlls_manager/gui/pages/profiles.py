"""Profiles page — edit and save profiles."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from dlls_manager.profile_db import list_profiles, load_profile, apply_profile_updates
from dlls_manager.dlss_catalog import load_dlss_versions


PRESET_TOOLTIPS = {
    "latest": "Always use the newest available preset",
    "j": "DLSS 4 Transformer preset J",
    "k": "DLSS 4 Transformer preset K (Quality/Balanced)",
    "l": "DLSS 4.5 Transformer preset L",
    "m": "DLSS 4.5 Transformer preset M (Performance)",
}


class ProfilesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._build_ui()
        self._load_profiles()

    def refresh(self) -> None:
        self._load_profiles()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)

        # Left: profile list
        left = QVBoxLayout()
        title = QLabel("Profiles")
        title.setObjectName("page_title")
        left.addWidget(title)

        self.profile_list = QListWidget()
        self.profile_list.setObjectName("profile_list")
        self.profile_list.currentRowChanged.connect(self._on_select_profile)
        left.addWidget(self.profile_list)
        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(250)
        layout.addWidget(left_widget)

        # Right: editor form
        form = QVBoxLayout()

        self.profile_name_label = QLabel("Select a profile")
        self.profile_name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #66c0f4;")
        form.addWidget(self.profile_name_label)

        # DLSS version
        form.addWidget(QLabel("DLSS Version"))
        self.dlss_version = QComboBox()
        self.dlss_version.setObjectName("profile_dlss_version")
        self.dlss_version.setToolTip("Select a downloaded DLSS version, or (none) to use game default")
        form.addWidget(self.dlss_version)

        # SR preset
        form.addWidget(QLabel("DLSS SR Preset (Super Resolution)"))
        self.sr_preset = QComboBox()
        self.sr_preset.setObjectName("profile_dlss_sr_preset")
        self.sr_preset.addItems(["(none)", "latest", "j", "k", "l", "m"])
        for i, label in enumerate(["(none)", "latest", "j", "k", "l", "m"]):
            if label in PRESET_TOOLTIPS:
                self.sr_preset.setItemData(i, PRESET_TOOLTIPS[label], Qt.ItemDataRole.ToolTipRole)
        self.sr_preset.setToolTip("Override the Super Resolution render preset")
        form.addWidget(self.sr_preset)

        # RR preset
        form.addWidget(QLabel("DLSS RR Preset (Ray Reconstruction)"))
        self.rr_preset = QComboBox()
        self.rr_preset.setObjectName("profile_dlss_rr_preset")
        self.rr_preset.addItems(["(none)", "latest", "j", "k", "l", "m"])
        for i, label in enumerate(["(none)", "latest", "j", "k", "l", "m"]):
            if label in PRESET_TOOLTIPS:
                self.rr_preset.setItemData(i, PRESET_TOOLTIPS[label], Qt.ItemDataRole.ToolTipRole)
        self.rr_preset.setToolTip("Override the Ray Reconstruction render preset")
        form.addWidget(self.rr_preset)

        # FG override
        form.addWidget(QLabel("DLSS FG Override (Frame Generation)"))
        self.fg_override = QComboBox()
        self.fg_override.setObjectName("profile_dlss_fg_override")
        self.fg_override.addItems(["(none)", "on", "off"])
        self.fg_override.setToolTip("Force Frame Generation on or off")
        form.addWidget(self.fg_override)

        # PROTON_DLSS_UPGRADE
        form.addWidget(QLabel("PROTON_DLSS_UPGRADE"))
        self.proton_dlss_upgrade = QLineEdit()
        self.proton_dlss_upgrade.setObjectName("profile_proton_dlss_upgrade")
        self.proton_dlss_upgrade.setPlaceholderText("e.g. 1 or 310.7 (leave empty for off)")
        self.proton_dlss_upgrade.setToolTip("Set to '1' for auto-upgrade, or a specific version like '310.7'")
        form.addWidget(self.proton_dlss_upgrade)

        # Launch args
        form.addWidget(QLabel("Launch Args"))
        self.launch_args = QLineEdit()
        self.launch_args.setObjectName("profile_launch_args")
        self.launch_args.setToolTip("Extra arguments appended to the launch command")
        form.addWidget(self.launch_args)

        # Custom env
        form.addWidget(QLabel("Custom Env Vars"))
        self.custom_env = QTextEdit()
        self.custom_env.setObjectName("profile_custom_env")
        self.custom_env.setPlaceholderText("KEY=value (one per line)")
        self.custom_env.setMaximumHeight(80)
        self.custom_env.setToolTip("Custom environment variables, one KEY=value per line")
        form.addWidget(self.custom_env)

        # Toggles — two rows for better layout
        toggle_row1 = QHBoxLayout()
        self.enable_nvapi = QCheckBox("NVAPI")
        self.enable_nvapi.setObjectName("profile_enable_nvapi")
        self.enable_nvapi.setToolTip("PROTON_ENABLE_NVAPI + DXVK_ENABLE_NVAPI")
        self.enable_smooth_motion = QCheckBox("Smooth Motion")
        self.enable_smooth_motion.setObjectName("profile_enable_smooth_motion")
        self.enable_smooth_motion.setToolTip("NVPRESENT_ENABLE_SMOOTH_MOTION")
        self.use_gamemode = QCheckBox("GameMode")
        self.use_gamemode.setObjectName("profile_use_gamemode")
        self.use_gamemode.setToolTip("gamemoderun wrapper")
        self.use_mangohud = QCheckBox("MangoHud")
        self.use_mangohud.setObjectName("profile_use_mangohud")
        self.use_mangohud.setToolTip("mangohud overlay wrapper")
        for cb in (self.enable_nvapi, self.enable_smooth_motion, self.use_gamemode, self.use_mangohud):
            toggle_row1.addWidget(cb)

        toggle_row2 = QHBoxLayout()
        self.enable_ngx_updater = QCheckBox("NGX Updater")
        self.enable_ngx_updater.setObjectName("profile_enable_ngx_updater")
        self.enable_ngx_updater.setToolTip("PROTON_ENABLE_NGX_UPDATER=1 — auto-update NGX DLLs")
        self.enable_hags = QCheckBox("HAGS")
        self.enable_hags.setObjectName("profile_enable_hags")
        self.enable_hags.setToolTip("WINEHAGS=1 — needed for Frame Generation")
        self.enable_vkreflex = QCheckBox("VKReflex")
        self.enable_vkreflex.setObjectName("profile_enable_vkreflex")
        self.enable_vkreflex.setToolTip("DXVK_NVAPI_VKREFLEX=1 — lower input latency")
        for cb in (self.enable_ngx_updater, self.enable_hags, self.enable_vkreflex):
            toggle_row2.addWidget(cb)

        toggle_widget = QWidget()
        toggle_layout = QVBoxLayout()
        toggle_layout.addLayout(toggle_row1)
        toggle_layout.addLayout(toggle_row2)
        toggle_widget.setLayout(toggle_layout)
        form.addWidget(toggle_widget)

        # Safety mode
        form.addWidget(QLabel("Safety Mode"))
        self.safety_mode = QComboBox()
        self.safety_mode.setObjectName("profile_safety_mode")
        self.safety_mode.addItems(["strict", "balanced", "unsafe"])
        self.safety_mode.setToolTip("strict: block risky overrides, balanced: warn, unsafe: allow all")
        form.addWidget(self.safety_mode)

        # Save button
        self.save_btn = QPushButton("  💾  Save Profile")
        self.save_btn.setObjectName("save_profile_button")
        self.save_btn.setToolTip("Save profile changes")
        self.save_btn.clicked.connect(self._on_save)
        form.addWidget(self.save_btn)

        # Result
        self.result_label = QLabel("")
        self.result_label.setObjectName("profile_result")
        form.addWidget(self.result_label)

        form.addStretch()
        form_widget = QWidget()
        form_widget.setLayout(form)
        layout.addWidget(form_widget, stretch=2)

    def _load_profiles(self) -> None:
        self.profile_list.clear()
        for name in list_profiles():
            QListWidgetItem(name, self.profile_list)
        if self.profile_list.count() > 0:
            self.profile_list.setCurrentRow(0)

    def _on_select_profile(self, row: int) -> None:
        if row < 0 or row >= self.profile_list.count():
            return
        name = self.profile_list.item(row).text()
        self._current_profile = name
        self.profile_name_label.setText(name)
        try:
            profile = load_profile(name)
        except Exception as e:
            self.result_label.setText(f"Error loading: {e}")
            return

        self.launch_args.setText(profile.get("launch_args", ""))
        self.enable_nvapi.setChecked(profile.get("enable_nvapi", False))
        self.enable_smooth_motion.setChecked(profile.get("enable_smooth_motion", False))
        self.use_gamemode.setChecked(profile.get("use_gamemode", False))
        self.use_mangohud.setChecked(profile.get("use_mangohud", False))
        self.enable_ngx_updater.setChecked(profile.get("enable_ngx_updater", False))
        self.enable_hags.setChecked(profile.get("enable_hags", False))
        self.enable_vkreflex.setChecked(profile.get("enable_vkreflex", False))

        # Custom env
        custom_env = profile.get("custom_env", {})
        if isinstance(custom_env, dict):
            self.custom_env.setPlainText(
                "\n".join(f"{k}={v}" for k, v in sorted(custom_env.items()))
            )
        else:
            self.custom_env.setPlainText("")

        # DLSS version combo
        self.dlss_version.clear()
        self.dlss_version.addItem("(none)", None)
        try:
            for entry in load_dlss_versions():
                self.dlss_version.addItem(entry["label"], entry["id"])
        except Exception:
            pass
        current_dlss = profile.get("dlss_version")
        if current_dlss:
            idx = self.dlss_version.findData(current_dlss)
            if idx >= 0:
                self.dlss_version.setCurrentIndex(idx)

        # Presets
        sr = profile.get("dlss_sr_preset")
        if sr:
            idx = self.sr_preset.findText(sr)
            if idx >= 0:
                self.sr_preset.setCurrentIndex(idx)
        else:
            self.sr_preset.setCurrentIndex(0)

        rr = profile.get("dlss_rr_preset")
        if rr:
            idx = self.rr_preset.findText(rr)
            if idx >= 0:
                self.rr_preset.setCurrentIndex(idx)
        else:
            self.rr_preset.setCurrentIndex(0)

        fg = profile.get("dlss_fg_override")
        if fg:
            idx = self.fg_override.findText(fg)
            if idx >= 0:
                self.fg_override.setCurrentIndex(idx)
        else:
            self.fg_override.setCurrentIndex(0)

        upgrade = profile.get("proton_dlss_upgrade")
        self.proton_dlss_upgrade.setText(upgrade or "")

        sm = profile.get("safety_mode", "strict")
        idx = self.safety_mode.findText(sm)
        if idx >= 0:
            self.safety_mode.setCurrentIndex(idx)

    def _on_save(self) -> None:
        if not hasattr(self, "_current_profile"):
            return
        name = self._current_profile

        sr = self.sr_preset.currentText()
        sr = None if sr == "(none)" else sr
        rr = self.rr_preset.currentText()
        rr = None if rr == "(none)" else rr
        fg = self.fg_override.currentText()
        fg = None if fg == "(none)" else fg
        upgrade = self.proton_dlss_upgrade.text().strip()
        upgrade = None if not upgrade else upgrade

        # Parse custom env
        custom_env: dict[str, str] = {}
        for line in self.custom_env.toPlainText().strip().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                custom_env[k.strip()] = v.strip()

        updates = {
            "launch_args": self.launch_args.text(),
            "enable_nvapi": self.enable_nvapi.isChecked(),
            "enable_smooth_motion": self.enable_smooth_motion.isChecked(),
            "use_gamemode": self.use_gamemode.isChecked(),
            "use_mangohud": self.use_mangohud.isChecked(),
            "enable_ngx_updater": self.enable_ngx_updater.isChecked(),
            "enable_hags": self.enable_hags.isChecked(),
            "enable_vkreflex": self.enable_vkreflex.isChecked(),
            "dlss_sr_preset": sr,
            "dlss_rr_preset": rr,
            "dlss_fg_override": fg,
            "proton_dlss_upgrade": upgrade,
            "safety_mode": self.safety_mode.currentText(),
            "dlss_version": self.dlss_version.currentData(),
            "custom_env": custom_env,
        }
        try:
            apply_profile_updates(name, updates)
            self.result_label.setText("Profile saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save profile:\n{e}")