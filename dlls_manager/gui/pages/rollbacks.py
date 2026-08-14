"""Rollbacks page — view and execute rollbacks."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from dlls_manager.mutations import list_rollbacks, rollback_mutation
from dlls_manager.gui.workers import JobWorker


class RollbacksPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker: JobWorker | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Rollback Manifests")
        title.setObjectName("page_title")
        layout.addWidget(title)

        # Header
        header = QHBoxLayout()
        self.refresh_btn = QPushButton("  🔄  Refresh")
        self.refresh_btn.setObjectName("refresh_rollbacks_button")
        self.refresh_btn.setToolTip("Reload rollback list")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)
        header.addStretch()
        layout.addLayout(header)

        self.rollback_table = QTableWidget()
        self.rollback_table.setObjectName("rollback_table")
        self.rollback_table.setColumnCount(5)
        self.rollback_table.setHorizontalHeaderLabels(
            ["Rollback ID", "Install", "Profile", "Created", "Files"]
        )
        self.rollback_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.rollback_table)

        self.execute_btn = QPushButton("  ↩️  Restore Selected")
        self.execute_btn.setObjectName("execute_rollback_button")
        self.execute_btn.setToolTip("Restore files from the selected rollback snapshot")
        self.execute_btn.clicked.connect(self._on_execute)
        layout.addWidget(self.execute_btn)

        self.empty_state_label = QLabel("No rollbacks found.\nApply a change first to create rollback snapshots.")
        self.empty_state_label.setObjectName("empty_state_label")
        self.empty_state_label.setStyleSheet("color: #8f98a0; padding: 20px; text-align: center;")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_state_label)

        self.result_label = QLabel("")
        self.result_label.setObjectName("rollback_result")
        layout.addWidget(self.result_label)

    def refresh(self) -> None:
        try:
            rollbacks = list_rollbacks()
        except Exception:
            rollbacks = []
        has_rollbacks = len(rollbacks) > 0
        self.rollback_table.setVisible(has_rollbacks)
        self.execute_btn.setVisible(has_rollbacks)
        self.rollback_table.setRowCount(len(rollbacks))
        for row, entry in enumerate(rollbacks):
            self.rollback_table.setItem(row, 0, QTableWidgetItem(entry.get("rollback_id", "")))
            self.rollback_table.setItem(row, 1, QTableWidgetItem(entry.get("install_id", "")))
            self.rollback_table.setItem(row, 2, QTableWidgetItem(entry.get("profile", "")))
            self.rollback_table.setItem(row, 3, QTableWidgetItem(entry.get("created_at", "")))
            self.rollback_table.setItem(row, 4, QTableWidgetItem(str(entry.get("files", 0))))
        self.empty_state_label.setVisible(not has_rollbacks)

    def _on_execute(self) -> None:
        row = self.rollback_table.currentRow()
        if row < 0:
            return
        rb_id = self.rollback_table.item(row, 0).text()
        file_count = self.rollback_table.item(row, 4).text()
        reply = QMessageBox.question(
            self, "Confirm Rollback",
            f"Restore rollback '{rb_id}'?\nThis will restore {file_count} file(s) to their previous state.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.result_label.setText("Rolling back...")
        self._worker = JobWorker(rollback_mutation, rb_id)
        self._worker.finished_job.connect(lambda r: self.result_label.setText(
            f"Rollback {'completed' if r.get('ok') else 'failed'}: {r.get('errors', [])}"))
        self._worker.error.connect(lambda e: QMessageBox.critical(self, "Rollback Error", e))
        self._worker.start()