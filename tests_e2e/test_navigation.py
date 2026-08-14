from dlls_manager.gui.main_window import MainWindow
from tests_e2e.conftest import select_sidebar_item, get_list_widget_items


class TestNavigation:
    def test_sidebar_has_five_entries(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        items = get_list_widget_items(window, "sidebar")
        assert len(items) == 5
        assert "Library" in items[0]
        window.close()

    def test_default_page_is_library(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
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
        for i in range(5):
            select_sidebar_item(window, i)
            assert window.stacked_widget.currentIndex() == i
        select_sidebar_item(window, 0)
        assert window.stacked_widget.currentIndex() == 0
        window.close()