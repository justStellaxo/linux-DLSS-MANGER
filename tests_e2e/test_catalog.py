from pathlib import Path
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

    def test_catalog_has_download_button(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        # At least one non-default version should have a download button
        has_download = False
        for row in range(window.catalog_page.catalog_table.rowCount()):
            widget = window.catalog_page.catalog_table.cellWidget(row, 7)
            if widget is not None:
                has_download = True
                break
        assert has_download
        window.close()

    def test_catalog_has_progress_bar(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        assert window.catalog_page.progress is not None
        window.close()

    def test_catalog_has_empty_state(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        assert window.catalog_page.empty_label is not None
        window.close()