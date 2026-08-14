import zipfile
import pytest
from dlls_manager.dlss_catalog import extract_all_dlss_dlls_from_zip


class TestExtractAllDlssDlls:
    def test_extracts_all_three_dlls(self, dlss_zip_with_three_dlls, tmp_path):
        target_dir = tmp_path / "runtime"
        extracted = extract_all_dlss_dlls_from_zip(dlss_zip_with_three_dlls, target_dir)
        assert set(extracted) == {"nvngx_dlss.dll", "nvngx_dlssd.dll", "nvngx_dlssg.dll"}
        assert (target_dir / "nvngx_dlss.dll").read_bytes() == b"sr-dll-bytes"
        assert (target_dir / "nvngx_dlssd.dll").read_bytes() == b"rr-dll-bytes"
        assert (target_dir / "nvngx_dlssg.dll").read_bytes() == b"fg-dll-bytes"

    def test_extracts_only_available_dlls(self, tmp_path):
        zip_path = tmp_path / "partial.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("bin/nvngx_dlss.dll", b"sr-only")
        target_dir = tmp_path / "runtime"
        extracted = extract_all_dlss_dlls_from_zip(zip_path, target_dir)
        assert extracted == ["nvngx_dlss.dll"]
        assert not (target_dir / "nvngx_dlssd.dll").exists()

    def test_returns_empty_list_for_zip_without_dlls(self, tmp_path):
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("readme.txt", b"no dlls here")
        target_dir = tmp_path / "runtime"
        extracted = extract_all_dlss_dlls_from_zip(zip_path, target_dir)
        assert extracted == []

    def test_overwrites_existing_dlls(self, dlss_zip_with_three_dlls, tmp_path):
        target_dir = tmp_path / "runtime"
        target_dir.mkdir()
        (target_dir / "nvngx_dlss.dll").write_bytes(b"old-bytes")
        extract_all_dlss_dlls_from_zip(dlss_zip_with_three_dlls, target_dir)
        assert (target_dir / "nvngx_dlss.dll").read_bytes() == b"sr-dll-bytes"