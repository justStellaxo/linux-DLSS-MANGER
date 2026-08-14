from dlls_manager.gui.main_window import MainWindow
from tests_e2e.conftest import select_sidebar_item


class TestCatalogPage:
    def test_catalog_table_has_entries(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        assert window.catalog_page.catalog_table.rowCount() >= 1
        window.close()

    def test_catalog_has_8_columns(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        assert window.catalog_page.catalog_table.columnCount() == 8
        window.close()