"""System page — system capability detection."""
from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from dlls_manager.detector import detect_capabilities
from dlls_manager.gui.workers import JobWorker


class SystemPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker: JobWorker | None = None
        self._build_ui()
        self._detect()

    def refresh(self) -> None:
        self._detect()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("System Information")
        title.setObjectName("page_title")
        layout.addWidget(title)

        self.info_label = QLabel("Detecting...")
        self.info_label.setObjectName("system_info")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-family: monospace; white-space: pre;")
        self.info_label.setToolTip("Detected system capabilities")
        layout.addWidget(self.info_label)

        btn_row = QVBoxLayout()
        self.redetect_btn = QPushButton("  🔄  Re-detect")
        self.redetect_btn.setObjectName("redetect_button")
        self.redetect_btn.setToolTip("Re-run system capability detection")
        self.redetect_btn.clicked.connect(self._detect)
        btn_row.addWidget(self.redetect_btn)

        self.copy_btn = QPushButton("  📋  Copy to Clipboard")
        self.copy_btn.setObjectName("copy_system_button")
        self.copy_btn.setToolTip("Copy system info to clipboard")
        self.copy_btn.clicked.connect(self._copy_info)
        btn_row.addWidget(self.copy_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

    def _detect(self) -> None:
        # Wait for any existing worker before starting a new one
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        self.info_label.setText("Detecting...")
        self._worker = JobWorker(detect_capabilities)
        self._worker.finished_job.connect(self._on_detect_done)
        self._worker.error.connect(lambda e: self.info_label.setText(f"Error: {e}"))
        self._worker.start()

    def _on_detect_done(self, report: dict) -> None:
        lines = []
        lines.append(f"OS: {report.get('os', '?')}")
        lines.append(f"Python: {report.get('python', '?')}")

        nvidia = report.get("nvidia_smi", "")
        if nvidia and nvidia != "nvidia-smi not found":
            lines.append(f"GPU: {nvidia}")
        else:
            lines.append("GPU: nvidia-smi not found")

        def status_icon(available: bool) -> str:
            return "✅" if available else "❌"

        lines.append(f"Vulkan: {status_icon(report.get('vulkan_available', False))}")
        lines.append(f"Steam: {status_icon(report.get('steam_available', False))}")
        lines.append(f"MangoHud: {status_icon(report.get('mangohud_available', False))}")
        lines.append(f"GameMode: {status_icon(report.get('gamemode_available', False))}")
        lines.append(f"Gamescope: {status_icon(report.get('gamescope_available', False))}")
        lines.append(f"Smooth Motion: {'✅ supported' if report.get('smooth_motion_supported') else '❌ not supported'}")

        self._report_text = "\n".join(lines)
        self.info_label.setText(self._report_text)

    def _copy_info(self) -> None:
        text = getattr(self, "_report_text", self.info_label.text())
        QGuiApplication.clipboard().setText(text)

    def cleanup(self) -> None:
        """Wait for the worker thread to finish to prevent segfaults on close."""
        worker = getattr(self, "_worker", None)
        if worker is not None and worker.isRunning():
            worker.quit()
            worker.wait(3000)