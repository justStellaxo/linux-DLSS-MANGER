from dlls_manager.gui.main_window import MainWindow
from tests_e2e.conftest import select_sidebar_item


class TestNavigation:
    def test_sidebar_has_five_entries(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.sidebar.count() == 5
        window.close()

    def test_default_page_is_library(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.sidebar.currentRow() == 0
        assert window.stacked_widget.currentIndex() == 0
        window.close()

    def test_click_catalog(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        assert window.stacked_widget.currentIndex() == 1
        window.close()

    def test_click_profiles(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        assert window.stacked_widget.currentIndex() == 2
        window.close()

    def test_click_rollbacks(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 3)
        assert window.stacked_widget.currentIndex() == 3
        window.close()

    def test_click_system(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 4)
        assert window.stacked_widget.currentIndex() == 4
        window.close()

    def test_back_to_library(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 4)
        select_sidebar_item(window, 0)
        assert window.stacked_widget.currentIndex() == 0
        window.close()

    def test_sidebar_has_icons(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        for i in range(5):
            text = window.sidebar.item(i).text()
            # Each sidebar item should have a non-ASCII icon prefix
            assert any(ord(c) > 0x2000 for c in text), f"Sidebar item {i} has no icon: {text!r}"
        window.close()

    def test_menu_bar_exists(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        menubar = window.menuBar()
        assert menubar is not None
        actions = menubar.actions()
        assert len(actions) >= 2  # File + Help
        window.close()

    def test_status_bar_exists(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.statusBar() is not None
        window.close()