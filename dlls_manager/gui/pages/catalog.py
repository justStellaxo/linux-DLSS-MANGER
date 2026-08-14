"""Catalog page — DLSS version management."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QProgressBar, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from dlls_manager.dlss_catalog import load_dlss_versions, refresh_dlss_catalog, download_dlss_version
from dlls_manager.gui.workers import JobWorker


class CatalogPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker: JobWorker | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Page title
        title = QLabel("DLSS Catalog")
        title.setObjectName("page_title")
        layout.addWidget(title)

        # Header bar
        header = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("catalog_search")
        self.search.setPlaceholderText("Search versions...")
        self.search.textChanged.connect(self._filter)
        header.addWidget(self.search)

        self.refresh_btn = QPushButton("  🔄  Refresh Catalog")
        self.refresh_btn.setObjectName("refresh_catalog_button")
        self.refresh_btn.setToolTip("Fetch latest DLSS releases from NVIDIA's GitHub")
        self.refresh_btn.clicked.connect(self._run_refresh)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        # Progress bar (hidden by default)
        self.progress = QProgressBar()
        self.progress.setObjectName("catalog_progress")
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        # Table
        self.catalog_table = QTableWidget()
        self.catalog_table.setObjectName("catalog_table")
        self.catalog_table.setColumnCount(8)
        self.catalog_table.setHorizontalHeaderLabels(
            ["Version", "Label", "Published", "SR", "RR", "FG", "Downloaded", "Action"]
        )
        self.catalog_table.horizontalHeader().setStretchLastSection(True)
        self.catalog_table.setToolTip("DLSS SDK versions from NVIDIA's GitHub releases")
        layout.addWidget(self.catalog_table)

        # Empty state
        self.empty_label = QLabel("No DLSS versions found.\nClick Refresh Catalog to fetch from NVIDIA.")
        self.empty_label.setObjectName("empty_state_label")
        self.empty_label.setStyleSheet("color: #8f98a0; padding: 20px; text-align: center;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

    def refresh(self) -> None:
        try:
            self._versions = load_dlss_versions()
        except Exception:
            self._versions = []
        self._populate_table()

    def _populate_table(self) -> None:
        has_versions = len(self._versions) > 0
        self.catalog_table.setVisible(has_versions)
        self.empty_label.setVisible(not has_versions)
        self.catalog_table.setRowCount(len(self._versions))
        for row, entry in enumerate(self._versions):
            self.catalog_table.setItem(row, 0, QTableWidgetItem(entry.get("id", "")))
            self.catalog_table.setItem(row, 1, QTableWidgetItem(entry.get("label", "")))
            self.catalog_table.setItem(row, 2, QTableWidgetItem(entry.get("published_at", "")[:10] if entry.get("published_at") else ""))
            sr = "✓" if entry.get("downloaded") else "✗"
            rr = "✓" if entry.get("has_rr_dll") else "✗"
            fg = "✓" if entry.get("has_fg_dll") else "✗"
            dl = "✓" if entry.get("downloaded") else "✗"
            sr_item = QTableWidgetItem(sr)
            sr_item.setToolTip("Super Resolution DLL")
            rr_item = QTableWidgetItem(rr)
            rr_item.setToolTip("Ray Reconstruction DLL")
            fg_item = QTableWidgetItem(fg)
            fg_item.setToolTip("Frame Generation DLL")
            self.catalog_table.setItem(row, 3, sr_item)
            self.catalog_table.setItem(row, 4, rr_item)
            self.catalog_table.setItem(row, 5, fg_item)
            self.catalog_table.setItem(row, 6, QTableWidgetItem(dl))

            if entry.get("id") != "game_default" and not entry.get("downloaded"):
                btn = QPushButton("  ⬇  Download")
                btn.setObjectName("catalog_download_button")
                btn.setToolTip(f"Download DLSS {entry.get('id', '?')}")
                btn.clicked.connect(lambda _, vid=entry["id"]: self._download_version(vid))
                self.catalog_table.setCellWidget(row, 7, btn)
            elif entry.get("id") != "game_default" and entry.get("downloaded"):
                btn = QPushButton("  ↻  Re-download")
                btn.setObjectName("catalog_redownload_button")
                btn.setToolTip("Re-download (overwrite existing)")
                btn.clicked.connect(lambda _, vid=entry["id"]: self._download_version(vid))
                self.catalog_table.setCellWidget(row, 7, btn)
            else:
                self.catalog_table.setItem(row, 7, QTableWidgetItem(""))

    def _filter(self, text: str) -> None:
        text_lower = text.lower()
        for row in range(self.catalog_table.rowCount()):
            item = self.catalog_table.item(row, 0)
            if item:
                self.catalog_table.setRowHidden(row, text_lower not in item.text().lower())

    def _run_refresh(self) -> None:
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("  🔄  Fetching...")
        self.progress.setVisible(True)
        self._worker = JobWorker(refresh_dlss_catalog)
        self._worker.finished_job.connect(self._on_refresh_done)
        self._worker.error.connect(self._on_refresh_error)
        self._worker.start()

    def _on_refresh_done(self, result: Any) -> None:
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("  🔄  Refresh Catalog")
        self.progress.setVisible(False)
        self.refresh()

    def _on_refresh_error(self, error: str) -> None:
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("  🔄  Refresh Catalog")
        self.progress.setVisible(False)
        QMessageBox.warning(self, "Catalog Refresh Error", f"Failed to fetch DLSS catalog:\n{error}")

    def _download_version(self, version_id: str) -> None:
        self.progress.setVisible(True)
        self._worker = JobWorker(download_dlss_version, version_id)
        self._worker.finished_job.connect(self._on_download_done)
        self._worker.error.connect(self._on_download_error)
        self._worker.start()

    def _on_download_done(self, result: Any) -> None:
        self.progress.setVisible(False)
        self.refresh()

    def _on_download_error(self, error: str) -> None:
        self.progress.setVisible(False)
        QMessageBox.warning(self, "Download Error", f"Failed to download DLSS version:\n{error}")