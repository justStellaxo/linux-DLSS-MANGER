from pathlib import Path
from dlls_manager.gui.main_window import MainWindow
from tests_e2e.conftest import (
    click_button, fill_line_edit, select_sidebar_item,
    check_checkbox, select_combobox,
)


class TestLibraryPage:
    def test_install_cards_rendered(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.library_page.install_list.count() >= 2
        window.close()

    def test_select_install_shows_detail(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        window.library_page.install_list.setCurrentRow(0)
        detail = window.library_page.detail_panel
        assert "Test Game" in detail.name_label.text()
        window.close()

    def test_search_filters_installs(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        fill_line_edit(window.library_page, "search_bar", "Blocked")
        visible = [i for i in range(window.library_page.install_list.count())
                   if not window.library_page.install_list.item(i).isHidden()]
        assert len(visible) == 1
        assert "Blocked" in window.library_page.install_list.item(visible[0]).text()
        window.close()

    def test_blocked_install_shows_blocked_badge(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        for i in range(window.library_page.install_list.count()):
            if "Blocked" in window.library_page.install_list.item(i).text():
                window.library_page.install_list.setCurrentRow(i)
                break
        detail = window.library_page.detail_panel
        assert "BLOCKED" in detail.status_label.text()
        window.close()

    def test_command_preview_shows_env_vars(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        window.library_page.install_list.setCurrentRow(0)
        detail = window.library_page.detail_panel
        assert detail.command_preview.toPlainText()
        window.close()

    def test_profile_selector_has_options(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        window.library_page.install_list.setCurrentRow(0)
        detail = window.library_page.detail_panel
        assert detail.profile_select.count() >= 1
        assert detail.profile_select.findText("default") >= 0
        window.close()

    def test_override_toggles_exist(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        window.library_page.install_list.setCurrentRow(0)
        detail = window.library_page.detail_panel
        # Check new toggles exist
        assert detail.override_smooth_motion is not None
        assert detail.override_hags is not None
        assert detail.override_vkreflex is not None
        assert detail.override_ngx_updater is not None
        window.close()

    def test_extra_env_editor_exists(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        window.library_page.install_list.setCurrentRow(0)
        detail = window.library_page.detail_panel
        assert detail.extra_env is not None
        window.close()

    def test_empty_state_shows_when_no_installs(self, qtbot, gui_env):
        from unittest.mock import patch
        with patch("dlls_manager.gui.pages.library.list_installs_summary", return_value=[]):
            window = MainWindow()
            qtbot.addWidget(window)
            qtbot.wait(500)
            assert window.library_page.install_list.count() == 0
            assert not window.library_page.empty_label.isHidden()
            window.close()