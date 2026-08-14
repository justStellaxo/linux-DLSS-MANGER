"""Main window for DLSS Manager standalone GUI."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QStackedWidget, QWidget,
)

from dlls_manager.gui.pages.library import LibraryPage
from dlls_manager.gui.pages.catalog import CatalogPage
from dlls_manager.gui.pages.profiles import ProfilesPage
from dlls_manager.gui.pages.rollbacks import RollbacksPage
from dlls_manager.gui.pages.system import SystemPage


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

    def _on_page_change(self, row: int) -> None:
        self.stacked_widget.setCurrentIndex(row)
        # Refresh pages when navigated to
        if row == 0:
            self.library_page.refresh()
        elif row == 1:
            self.catalog_page.refresh()
        elif row == 3:
            self.rollbacks_page.refresh()
        elif row == 4:
            self.system_page.refresh()