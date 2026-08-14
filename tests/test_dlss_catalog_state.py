import pytest
from pathlib import Path
from unittest.mock import patch
from dlls_manager.dlss_catalog import _with_local_state


class TestCatalogLocalState:
    def test_all_three_dlls_present(self, tmp_path):
        runtime_dir = tmp_path / "dlss_runtime" / "310.7.0"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "nvngx_dlss.dll").write_bytes(b"sr")
        (runtime_dir / "nvngx_dlssd.dll").write_bytes(b"rr")
        (runtime_dir / "nvngx_dlssg.dll").write_bytes(b"fg")
        entry = {"id": "310.7.0", "label": "DLSS 310.7.0", "selectable": True}
        with patch("dlls_manager.dlss_catalog.DLSS_RUNTIME_DIR", tmp_path / "dlss_runtime"):
            result = _with_local_state(entry)
        assert result["downloaded"] is True
        assert result["has_rr_dll"] is True
        assert result["has_fg_dll"] is True

    def test_only_sr_dll_present(self, tmp_path):
        runtime_dir = tmp_path / "dlss_runtime" / "3.7.10"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "nvngx_dlss.dll").write_bytes(b"sr")
        entry = {"id": "3.7.10", "label": "DLSS 3.7.10", "selectable": True}
        with patch("dlls_manager.dlss_catalog.DLSS_RUNTIME_DIR", tmp_path / "dlss_runtime"):
            result = _with_local_state(entry)
        assert result["downloaded"] is True
        assert result["has_rr_dll"] is False
        assert result["has_fg_dll"] is False

    def test_no_dlls_present(self, tmp_path):
        runtime_dir = tmp_path / "dlss_runtime" / "999.0.0"
        runtime_dir.mkdir(parents=True)
        entry = {"id": "999.0.0", "label": "DLSS 999", "selectable": True}
        with patch("dlls_manager.dlss_catalog.DLSS_RUNTIME_DIR", tmp_path / "dlss_runtime"):
            result = _with_local_state(entry)
        assert result["downloaded"] is False
        assert result["has_rr_dll"] is False
        assert result["has_fg_dll"] is False

    def test_game_default_never_has_dlls(self, tmp_path):
        entry = {"id": "game_default", "label": "Game Default", "selectable": True}
        with patch("dlls_manager.dlss_catalog.DLSS_RUNTIME_DIR", tmp_path / "dlss_runtime"):
            result = _with_local_state(entry)
        assert result["downloaded"] is False
        assert result["has_rr_dll"] is False
        assert result["has_fg_dll"] is False