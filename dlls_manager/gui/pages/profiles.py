"""Profiles page — edit and save profiles."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from dlls_manager.profile_db import list_profiles, load_profile, apply_profile_updates
from dlls_manager.dlss_catalog import load_dlss_versions


class ProfilesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._build_ui()
        self._load_profiles()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)

        # Left: profile list
        self.profile_list = QListWidget()
        self.profile_list.setObjectName("profile_list")
        self.profile_list.currentRowChanged.connect(self._on_select_profile)
        layout.addWidget(self.profile_list, stretch=1)

        # Right: editor form
        form = QVBoxLayout()

        self.profile_name_label = QLabel("Select a profile")
        self.profile_name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #66c0f4;")
        form.addWidget(self.profile_name_label)

        # DLSS version
        form.addWidget(QLabel("DLSS Version"))
        self.dlss_version = QComboBox()
        self.dlss_version.setObjectName("profile_dlss_version")
        form.addWidget(self.dlss_version)

        # SR preset
        form.addWidget(QLabel("DLSS SR Preset"))
        self.sr_preset = QComboBox()
        self.sr_preset.setObjectName("profile_dlss_sr_preset")
        self.sr_preset.addItems(["(none)", "latest", "j", "k", "l", "m"])
        form.addWidget(self.sr_preset)

        # RR preset
        form.addWidget(QLabel("DLSS RR Preset"))
        self.rr_preset = QComboBox()
        self.rr_preset.setObjectName("profile_dlss_rr_preset")
        self.rr_preset.addItems(["(none)", "latest", "j", "k", "l", "m"])
        form.addWidget(self.rr_preset)

        # FG override
        form.addWidget(QLabel("DLSS FG Override"))
        self.fg_override = QComboBox()
        self.fg_override.setObjectName("profile_dlss_fg_override")
        self.fg_override.addItems(["(none)", "on", "off"])
        form.addWidget(self.fg_override)

        # PROTON_DLSS_UPGRADE
        form.addWidget(QLabel("PROTON_DLSS_UPGRADE"))
        self.proton_dlss_upgrade = QLineEdit()
        self.proton_dlss_upgrade.setObjectName("profile_proton_dlss_upgrade")
        self.proton_dlss_upgrade.setPlaceholderText("e.g. 1 or 310.7")
        form.addWidget(self.proton_dlss_upgrade)

        # Launch args
        form.addWidget(QLabel("Launch Args"))
        self.launch_args = QLineEdit()
        self.launch_args.setObjectName("profile_launch_args")
        form.addWidget(self.launch_args)

        # Toggles
        toggle_row = QHBoxLayout()
        self.enable_nvapi = QCheckBox("NVAPI")
        self.enable_nvapi.setObjectName("profile_enable_nvapi")
        self.enable_smooth_motion = QCheckBox("Smooth Motion")
        self.enable_smooth_motion.setObjectName("profile_enable_smooth_motion")
        self.use_gamemode = QCheckBox("GameMode")
        self.use_gamemode.setObjectName("profile_use_gamemode")
        self.use_mangohud = QCheckBox("MangoHud")
        self.use_mangohud.setObjectName("profile_use_mangohud")
        self.enable_ngx_updater = QCheckBox("NGX Updater")
        self.enable_ngx_updater.setObjectName("profile_enable_ngx_updater")
        self.enable_hags = QCheckBox("HAGS")
        self.enable_hags.setObjectName("profile_enable_hags")
        self.enable_vkreflex = QCheckBox("VKReflex")
        self.enable_vkreflex.setObjectName("profile_enable_vkreflex")
        for cb in (self.enable_nvapi, self.enable_smooth_motion, self.use_gamemode,
                   self.use_mangohud, self.enable_ngx_updater, self.enable_hags, self.enable_vkreflex):
            toggle_row.addWidget(cb)
        toggle_widget = QWidget()
        toggle_widget.setLayout(toggle_row)
        form.addWidget(toggle_widget)

        # Safety mode
        form.addWidget(QLabel("Safety Mode"))
        self.safety_mode = QComboBox()
        self.safety_mode.setObjectName("profile_safety_mode")
        self.safety_mode.addItems(["strict", "balanced", "unsafe"])
        form.addWidget(self.safety_mode)

        # Save button
        self.save_btn = QPushButton("Save Profile")
        self.save_btn.setObjectName("save_profile_button")
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
        }
        try:
            apply_profile_updates(name, updates)
            self.result_label.setText("Profile saved successfully.")
        except Exception as e:
            self.result_label.setText(f"Save error: {e}")