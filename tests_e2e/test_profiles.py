from dlls_manager.gui.main_window import MainWindow
from tests_e2e.conftest import (
    click_button, fill_line_edit, select_sidebar_item,
    check_checkbox, select_combobox,
)


class TestProfilesPage:
    def test_profiles_list_shows_default(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        assert window.profiles_page.profile_list.count() >= 1
        assert "default" in window.profiles_page.profile_list.item(0).text().lower()
        window.close()

    def test_select_profile_shows_form(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        window.profiles_page.profile_list.setCurrentRow(0)
        from PySide6.QtWidgets import QCheckBox
        nvapi_cb = window.profiles_page.findChild(QCheckBox, "profile_enable_nvapi")
        assert nvapi_cb is not None
        window.close()

    def test_preset_dropdown_has_options(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        window.profiles_page.profile_list.setCurrentRow(0)
        from PySide6.QtWidgets import QComboBox
        sr_combo = window.profiles_page.findChild(QComboBox, "profile_dlss_sr_preset")
        assert sr_combo is not None
        items = [sr_combo.itemText(i) for i in range(sr_combo.count())]
        assert "latest" in items
        assert "j" in items
        window.close()

    def test_edit_and_save_profile(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        window.profiles_page.profile_list.setCurrentRow(0)
        fill_line_edit(window.profiles_page, "profile_launch_args", "--test-args")
        check_checkbox(window.profiles_page, "profile_enable_nvapi", True)
        click_button(window.profiles_page, "save_profile_button")
        from dlls_manager.profile_db import load_profile
        profile = load_profile("default")
        assert profile["launch_args"] == "--test-args"
        assert profile["enable_nvapi"] is True
        window.close()