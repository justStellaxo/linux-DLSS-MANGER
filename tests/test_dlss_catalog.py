import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from dlls_manager.dlss_catalog import (
    build_dlss_catalog_from_releases,
    extract_nvngx_dlss_from_zip,
    load_dlss_versions,
)


class DlssCatalogTests(unittest.TestCase):
    def test_build_catalog_from_releases_sorts_descending_and_keeps_game_default(self) -> None:
        releases = [
            {
                "tag_name": "v3.7.10",
                "name": "DLSS 3.7.10 SDK",
                "html_url": "https://github.com/NVIDIA/DLSS/releases/tag/v3.7.10",
                "published_at": "2024-06-04T18:53:18Z",
                "assets": [
                    {
                        "name": "ngx_dlss_demo_windows.zip",
                        "browser_download_url": "https://example.invalid/3.7.10.zip",
                        "size": 123,
                        "content_type": "application/zip",
                    }
                ],
            },
            {
                "tag_name": "v310.5.3",
                "name": "DLSS 310.5.3 SDK",
                "html_url": "https://github.com/NVIDIA/DLSS/releases/tag/v310.5.3",
                "published_at": "2026-01-26T22:34:57Z",
                "assets": [
                    {
                        "name": "ngx_dlss_demo_windows.zip",
                        "browser_download_url": "https://example.invalid/310.5.3.zip",
                        "size": 456,
                        "content_type": "application/zip",
                    }
                ],
            },
        ]

        catalog = build_dlss_catalog_from_releases(releases)
        self.assertEqual(catalog[0]["id"], "game_default")
        self.assertEqual(catalog[1]["id"], "310.5.3")
        self.assertEqual(catalog[2]["id"], "3.7.10")
        self.assertEqual(catalog[1]["source"], "official_nvidia_github")

    def test_load_versions_enriches_local_download_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            versions_path = root / "dlss_versions.json"
            downloads_dir = root / "dlss_downloads"
            runtime_dir = root / "dlss_runtime"
            versions_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "game_default",
                            "label": "Game Default",
                            "selectable": True,
                        },
                        {
                            "id": "3.7.10",
                            "version": "3.7.10",
                            "label": "DLSS 3.7.10",
                            "selectable": True,
                            "source": "official_nvidia_github",
                            "release_name": "DLSS 3.7.10 SDK",
                            "release_url": "https://example.invalid/release",
                            "published_at": "2024-06-04T18:53:18Z",
                            "browser_download_url": "https://example.invalid/3.7.10.zip",
                            "asset_name": "ngx_dlss_demo_windows.zip",
                            "asset_size": 123,
                            "asset_content_type": "application/zip",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            (downloads_dir / "3.7.10").mkdir(parents=True)
            (downloads_dir / "3.7.10" / "ngx_dlss_demo_windows.zip").write_bytes(b"zip")
            (runtime_dir / "3.7.10").mkdir(parents=True)
            (runtime_dir / "3.7.10" / "nvngx_dlss.dll").write_bytes(b"dll")

            with (
                patch("dlls_manager.dlss_catalog.DLSS_VERSIONS_FILE", versions_path),
                patch("dlls_manager.dlss_catalog.DLSS_DOWNLOADS_DIR", downloads_dir),
                patch("dlls_manager.dlss_catalog.DLSS_RUNTIME_DIR", runtime_dir),
            ):
                versions = load_dlss_versions()

            downloaded = next(entry for entry in versions if entry["id"] == "3.7.10")
            self.assertTrue(downloaded["downloaded"])
            self.assertTrue(downloaded["local_asset_exists"])
            self.assertIn("download-dlss 3.7.10", downloaded["download_command"])

    def test_extract_nvngx_dlss_from_zip_writes_runtime_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zip_path = root / "sample.zip"
            target_path = root / "runtime" / "nvngx_dlss.dll"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("DLSS_Sample_App/bin/ngx_dlss_demo/nvngx_dlss.dll", b"dll-bytes")

            member_name = extract_nvngx_dlss_from_zip(zip_path, target_path)

            self.assertEqual(member_name, "DLSS_Sample_App/bin/ngx_dlss_demo/nvngx_dlss.dll")
            self.assertEqual(target_path.read_bytes(), b"dll-bytes")


if __name__ == "__main__":
    unittest.main()
