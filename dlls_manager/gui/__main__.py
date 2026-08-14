"""DLSS Manager GUI entry point."""
import sys

from PySide6.QtWidgets import QApplication

from dlls_manager.gui.main_window import MainWindow
from dlls_manager.gui.styles import DARK_THEME


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("DLSS Manager")
    app.setStyleSheet(DARK_THEME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()