from unittest.mock import patch

from dlls_manager.gui.main_window import MainWindow
from tests_e2e.conftest import select_sidebar_item


_FAKE_REPORT = {
    "os": "Linux Test",
    "python": "3.14.0",
    "nvidia_smi": "NVIDIA GeForce RTX 4090, 595.84",
    "vulkan_available": True,
    "steam_available": True,
    "mangohud_available": True,
    "gamemode_available": True,
    "gamescope_available": False,
    "smooth_motion_supported": True,
}


class TestSystemPage:
    def test_system_page_shows_info(self, qtbot, gui_with_installs):
        with patch("dlls_manager.gui.pages.system.detect_capabilities", return_value=_FAKE_REPORT):
            window = MainWindow()
            qtbot.addWidget(window)
            select_sidebar_item(window, 4)
            # Navigation triggers refresh() which starts a new worker;
            # call _on_detect_done directly since QThread signals are
            # unreliable in pytest-qt without a running event loop
            window.system_page._on_detect_done(_FAKE_REPORT)
            text = window.system_page.info_label.text()
            assert "OS:" in text
            assert "Linux Test" in text
            window.system_page.cleanup()
            window.close()


class TestRollbacksPage:
    def test_empty_rollbacks_shows_message(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 3)
        assert window.rollbacks_page.rollback_table.rowCount() == 0
        # isVisible() requires the widget to be shown; use the label's text instead
        assert window.rollbacks_page.empty_state_label.text()
        assert not window.rollbacks_page.empty_state_label.isHidden()
        window.close()