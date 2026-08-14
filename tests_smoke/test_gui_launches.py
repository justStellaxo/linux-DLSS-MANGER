from dlls_manager.gui.main_window import MainWindow
from dlls_manager.gui.__main__ import main


class TestGuiLaunches:
    def test_gui_window_opens_and_closes(self, qapp):
        window = MainWindow()
        assert window.windowTitle() == "DLSS Manager"
        window.close()

    def test_gui_has_five_sidebar_entries(self, qapp):
        window = MainWindow()
        from PySide6.QtWidgets import QListWidget
        sidebar = window.findChild(QListWidget, "sidebar")
        assert sidebar is not None
        assert sidebar.count() == 5
        window.close()

    def test_gui_app_entry_point_import(self):
        assert callable(main)