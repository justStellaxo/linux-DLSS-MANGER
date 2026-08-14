"""System page — system capability detection."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from dlls_manager.detector import detect_capabilities
from dlls_manager.gui.workers import JobWorker


class SystemPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._build_ui()
        self._detect()

    def refresh(self) -> None:
        self._detect()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("System Information")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        self.info_label = QLabel("Detecting...")
        self.info_label.setObjectName("system_info")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-family: monospace; white-space: pre;")
        layout.addWidget(self.info_label)

        self.redetect_btn = QPushButton("Re-detect")
        self.redetect_btn.setObjectName("redetect_button")
        self.redetect_btn.clicked.connect(self._detect)
        layout.addWidget(self.redetect_btn)

        layout.addStretch()

    def _detect(self) -> None:
        self.info_label.setText("Detecting...")
        self._worker = JobWorker(detect_capabilities)
        self._worker.finished_job.connect(self._on_detect_done)
        self._worker.error.connect(lambda e: self.info_label.setText(f"Error: {e}"))
        self._worker.start()

    def cleanup(self) -> None:
        """Wait for the worker thread to finish to prevent segfaults on close."""
        worker = getattr(self, "_worker", None)
        if worker is not None and worker.isRunning():
            worker.quit()
            worker.wait(3000)

    def _on_detect_done(self, report: dict) -> None:
        lines = []
        lines.append(f"OS: {report.get('os', '?')}")
        lines.append(f"Python: {report.get('python', '?')}")

        nvidia = report.get("nvidia_smi", "")
        if nvidia and nvidia != "nvidia-smi not found":
            lines.append(f"GPU: {nvidia}")
        else:
            lines.append("GPU: nvidia-smi not found")

        lines.append(f"Vulkan: {'available' if report.get('vulkan_available') else 'not found'}")
        lines.append(f"Steam: {'available' if report.get('steam_available') else 'not found'}")
        lines.append(f"MangoHud: {'available' if report.get('mangohud_available') else 'not found'}")
        lines.append(f"GameMode: {'available' if report.get('gamemode_available') else 'not found'}")
        lines.append(f"Gamescope: {'available' if report.get('gamescope_available') else 'not found'}")
        lines.append(f"Smooth Motion: {'supported' if report.get('smooth_motion_supported') else 'not supported'}")

        self.info_label.setText("\n".join(lines))