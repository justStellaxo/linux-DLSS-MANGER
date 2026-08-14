"""Main window for DLSS Manager standalone GUI."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QStackedWidget, QStatusBar, QWidget,
)

from dlls_manager.gui.pages.library import LibraryPage
from dlls_manager.gui.pages.catalog import CatalogPage
from dlls_manager.gui.pages.profiles import ProfilesPage
from dlls_manager.gui.pages.rollbacks import RollbacksPage
from dlls_manager.gui.pages.system import SystemPage

SIDEBAR_ICONS = {
    0: "🎮",   # Library
    1: "📦",   # Catalog
    2: "⚙️",   # Profiles
    3: "↩️",   # Rollbacks
    4: "🖥️",   # System
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DLSS Manager")
        self.setMinimumSize(1200, 800)

        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        for label in ["Library", "Catalog", "Profiles", "Rollbacks", "System"]:
            QListWidgetItem(label, self.sidebar)
        # Add icons
        for i, icon in SIDEBAR_ICONS.items():
            item = self.sidebar.item(i)
            if item:
                item.setText(f"  {icon}  {item.text()}")
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._on_page_change)
        main_layout.addWidget(self.sidebar)

        # Stacked pages
        self.stacked_widget = QStackedWidget()
        self.library_page = LibraryPage()
        self.catalog_page = CatalogPage()
        self.profiles_page = ProfilesPage()
        self.rollbacks_page = RollbacksPage()
        self.system_page = SystemPage()
        self.stacked_widget.addWidget(self.library_page)
        self.stacked_widget.addWidget(self.catalog_page)
        self.stacked_widget.addWidget(self.profiles_page)
        self.stacked_widget.addWidget(self.rollbacks_page)
        self.stacked_widget.addWidget(self.system_page)
        main_layout.addWidget(self.stacked_widget, stretch=1)

        self.setCentralWidget(central)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Menu bar
        self._build_menu()

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        QMessageBox.about(self, "About DLSS Manager",
            "DLSS Manager v0.2.0a1\n\n"
            "A Linux-native desktop app for managing DLSS versions,\n"
            "Proton launch options, and per-game overrides.\n\n"
            "Built with Python + PySide6 (Qt6)")

    def _on_page_change(self, row: int) -> None:
        self.stacked_widget.setCurrentIndex(row)
        # Refresh pages when navigated to
        if row == 0:
            self.library_page.refresh()
        elif row == 1:
            self.catalog_page.refresh()
        elif row == 2:
            self.profiles_page.refresh()
        elif row == 3:
            self.rollbacks_page.refresh()
        elif row == 4:
            self.system_page.refresh()

    def cleanup(self) -> None:
        """Clean up worker threads before close to prevent segfaults."""
        for page in (self.library_page, self.catalog_page,
                     self.rollbacks_page, self.system_page):
            worker = getattr(page, "_worker", None)
            if worker is not None and worker.isRunning():
                worker.quit()
                worker.wait(3000)
        self.system_page.cleanup()