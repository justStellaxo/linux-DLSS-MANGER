"""Catalog page — DLSS version management."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from dlls_manager.dlss_catalog import load_dlss_versions, refresh_dlss_catalog, download_dlss_version
from dlls_manager.gui.workers import JobWorker


class CatalogPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header bar
        header = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("catalog_search")
        self.search.setPlaceholderText("Search versions...")
        self.search.textChanged.connect(self._filter)
        header.addWidget(self.search)

        refresh_btn = QPushButton("Refresh Catalog")
        refresh_btn.setObjectName("refresh_catalog_button")
        refresh_btn.clicked.connect(self._run_refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # Table
        self.catalog_table = QTableWidget()
        self.catalog_table.setObjectName("catalog_table")
        self.catalog_table.setColumnCount(8)
        self.catalog_table.setHorizontalHeaderLabels(
            ["Version", "Label", "Published", "SR", "RR", "FG", "Downloaded", "Action"]
        )
        self.catalog_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.catalog_table)

    def refresh(self) -> None:
        try:
            self._versions = load_dlss_versions()
        except Exception:
            self._versions = []
        self._populate_table()

    def _populate_table(self) -> None:
        self.catalog_table.setRowCount(len(self._versions))
        for row, entry in enumerate(self._versions):
            self.catalog_table.setItem(row, 0, QTableWidgetItem(entry.get("id", "")))
            self.catalog_table.setItem(row, 1, QTableWidgetItem(entry.get("label", "")))
            self.catalog_table.setItem(row, 2, QTableWidgetItem(entry.get("published_at", "")[:10] if entry.get("published_at") else ""))
            sr = "✓" if entry.get("downloaded") else "✗"
            rr = "✓" if entry.get("has_rr_dll") else "✗"
            fg = "✓" if entry.get("has_fg_dll") else "✗"
            dl = "✓" if entry.get("downloaded") else "✗"
            self.catalog_table.setItem(row, 3, QTableWidgetItem(sr))
            self.catalog_table.setItem(row, 4, QTableWidgetItem(rr))
            self.catalog_table.setItem(row, 5, QTableWidgetItem(fg))
            self.catalog_table.setItem(row, 6, QTableWidgetItem(dl))

            if entry.get("id") != "game_default" and not entry.get("downloaded"):
                btn = QPushButton("Download")
                btn.setObjectName("catalog_download_button")
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
        self._worker = JobWorker(refresh_dlss_catalog)
        self._worker.finished_job.connect(lambda r: self.refresh())
        self._worker.error.connect(lambda e: print(f"Catalog refresh error: {e}"))
        self._worker.start()

    def _download_version(self, version_id: str) -> None:
        self._worker = JobWorker(download_dlss_version, version_id)
        self._worker.finished_job.connect(lambda r: self.refresh())
        self._worker.error.connect(lambda e: print(f"Download error: {e}"))
        self._worker.start()