from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.request import Request, urlopen

from dlls_manager.models import DlssVersionRecord
from dlls_manager.paths import DLSS_DOWNLOADS_DIR, DLSS_RUNTIME_DIR, DLSS_VERSIONS_FILE
from dlls_manager.utils import atomic_write_json, ensure_directory, load_json, utc_timestamp


GITHUB_DLSS_RELEASES_API = "https://api.github.com/repos/NVIDIA/DLSS/releases?per_page=100"
OFFICIAL_DLSS_RELEASES_PAGE = "https://github.com/NVIDIA/DLSS/releases"
HTTP_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "dlls-manager/0.2.0a1",
}


def normalize_version_id(value: str) -> str:
    return value[1:] if value.startswith("v") else value


def version_sort_key(version_id: str) -> tuple[int, ...]:
    normalized = normalize_version_id(version_id)
    parts = []
    for part in normalized.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits or "0"))
    return tuple(parts)


def compare_version_id(version_id: str) -> tuple[int, ...]:
    key = version_sort_key(version_id)
    return key + (0,) * (4 - len(key))


def validate_dlss_version(item: dict[str, Any], index: int) -> DlssVersionRecord:
    if "id" not in item or not isinstance(item["id"], str) or not item["id"].strip():
        raise ValueError(f"dlss_versions.json entry {index} must define a non-empty id string.")
    if "label" not in item or not isinstance(item["label"], str) or not item["label"].strip():
        raise ValueError(f"dlss_versions.json entry {index} must define a non-empty label string.")
    selectable = item.get("selectable")
    if not isinstance(selectable, bool):
        raise ValueError(f"dlss_versions.json entry {index} must define selectable as a boolean.")

    validated: DlssVersionRecord = {
        "id": item["id"],
        "label": item["label"],
        "selectable": selectable,
    }

    optional_string_fields = (
        "version",
        "source",
        "release_name",
        "release_url",
        "published_at",
        "browser_download_url",
        "asset_name",
        "asset_content_type",
        "local_asset_path",
        "runtime_path",
        "download_command",
    )
    for field in optional_string_fields:
        value = item.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"dlss_versions.json entry {index} field '{field}' must be a non-empty string.")
        validated[field] = value

    optional_int_fields = ("asset_size",)
    for field in optional_int_fields:
        value = item.get(field)
        if value is None:
            continue
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"dlss_versions.json entry {index} field '{field}' must be a non-negative integer.")
        validated[field] = value

    optional_bool_fields = ("downloaded", "local_asset_exists")
    for field in optional_bool_fields:
        value = item.get(field)
        if value is None:
            continue
        if not isinstance(value, bool):
            raise ValueError(f"dlss_versions.json entry {index} field '{field}' must be a boolean.")
        validated[field] = value

    return validated


def _request_json(url: str) -> Any:
    request = Request(url, headers=HTTP_HEADERS)
    with urlopen(request) as response:
        return json.load(response)


def _find_windows_asset(release: dict[str, Any]) -> dict[str, Any] | None:
    for asset in release.get("assets", []):
        name = str(asset.get("name", ""))
        if name.lower().endswith(".zip") and "windows" in name.lower():
            return asset
    return None


def build_dlss_catalog_from_releases(releases: list[dict[str, Any]]) -> list[DlssVersionRecord]:
    entries: list[DlssVersionRecord] = [
        {
            "id": "game_default",
            "version": "game_default",
            "label": "Game Default",
            "selectable": True,
            "source": "built_in",
            "release_name": "Use the game-shipped DLSS runtime",
            "release_url": OFFICIAL_DLSS_RELEASES_PAGE,
        }
    ]

    official_entries: list[DlssVersionRecord] = []
    for release in releases:
        tag_name = str(release.get("tag_name", "")).strip()
        if not tag_name:
            continue
        asset = _find_windows_asset(release)
        if asset is None:
            continue
        version = normalize_version_id(tag_name)
        official_entries.append(
            {
                "id": version,
                "version": version,
                "label": f"DLSS {version}",
                "selectable": True,
                "source": "official_nvidia_github",
                "release_name": str(release.get("name") or f"DLSS {version} SDK"),
                "release_url": str(release.get("html_url") or OFFICIAL_DLSS_RELEASES_PAGE),
                "published_at": str(release.get("published_at") or ""),
                "browser_download_url": str(asset.get("browser_download_url") or ""),
                "asset_name": str(asset.get("name") or ""),
                "asset_size": int(asset.get("size") or 0),
                "asset_content_type": str(asset.get("content_type") or "application/zip"),
            }
        )

    official_entries.sort(key=lambda item: compare_version_id(item["id"]), reverse=True)
    return entries + official_entries


def _with_local_state(entry: DlssVersionRecord) -> DlssVersionRecord:
    enriched: DlssVersionRecord = dict(entry)
    if entry["id"] == "game_default":
        enriched["downloaded"] = False
        enriched["local_asset_exists"] = False
        enriched["download_command"] = "not required"
        return enriched

    asset_name = entry.get("asset_name") or f"{entry['id']}.zip"
    asset_path = DLSS_DOWNLOADS_DIR / entry["id"] / asset_name
    runtime_path = DLSS_RUNTIME_DIR / entry["id"] / "nvngx_dlss.dll"
    enriched["local_asset_path"] = str(asset_path)
    enriched["runtime_path"] = str(runtime_path)
    enriched["local_asset_exists"] = asset_path.exists()
    enriched["downloaded"] = runtime_path.exists()
    enriched["download_command"] = f"python3 main.py download-dlss {entry['id']}"
    return enriched


def load_dlss_versions() -> list[DlssVersionRecord]:
    if not DLSS_VERSIONS_FILE.exists():
        return []
    versions = load_json(DLSS_VERSIONS_FILE)
    if not isinstance(versions, list):
        raise ValueError("dlss_versions.json must contain a top-level array.")
    return [_with_local_state(validate_dlss_version(item, index)) for index, item in enumerate(versions)]


def get_dlss_version(version_id: str) -> DlssVersionRecord:
    for entry in load_dlss_versions():
        if entry["id"] == version_id:
            return entry
    raise ValueError(f"DLSS version '{version_id}' is not present in dlss_versions.json.")


def refresh_dlss_catalog() -> dict[str, Any]:
    releases = _request_json(GITHUB_DLSS_RELEASES_API)
    if not isinstance(releases, list):
        raise ValueError("Unexpected GitHub API response while refreshing DLSS catalog.")
    catalog = build_dlss_catalog_from_releases(releases)
    atomic_write_json(DLSS_VERSIONS_FILE, catalog)
    return {
        "updated": True,
        "source": GITHUB_DLSS_RELEASES_API,
        "release_page": OFFICIAL_DLSS_RELEASES_PAGE,
        "entries": len(catalog),
        "downloadable_entries": len([entry for entry in catalog if entry["id"] != "game_default"]),
        "latest_version": next((entry["id"] for entry in catalog if entry["id"] != "game_default"), None),
        "catalog_path": str(DLSS_VERSIONS_FILE),
    }


def extract_nvngx_dlss_from_zip(zip_path: Path, target_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as archive:
        matching_names = [name for name in archive.namelist() if name.lower().endswith("/nvngx_dlss.dll")]
        if not matching_names:
            raise ValueError(f"Archive '{zip_path}' does not contain nvngx_dlss.dll.")
        member_name = matching_names[0]
        ensure_directory(target_path.parent)
        with archive.open(member_name) as source, NamedTemporaryFile(delete=False, dir=target_path.parent) as tmp:
            shutil.copyfileobj(source, tmp)
            tmp_path = Path(tmp.name)
    tmp_path.replace(target_path)
    return member_name


def download_dlss_version(version_id: str, force: bool = False) -> dict[str, Any]:
    entry = get_dlss_version(version_id)
    if entry["id"] == "game_default":
        raise ValueError("game_default does not have a downloadable DLSS payload.")

    download_url = entry.get("browser_download_url")
    if not download_url:
        raise ValueError(f"DLSS version '{version_id}' does not define an official download URL.")

    asset_dir = ensure_directory(DLSS_DOWNLOADS_DIR / version_id)
    runtime_dir = ensure_directory(DLSS_RUNTIME_DIR / version_id)
    asset_path = asset_dir / (entry.get("asset_name") or f"{version_id}.zip")
    runtime_path = runtime_dir / "nvngx_dlss.dll"
    metadata_path = runtime_dir / "download.json"

    if runtime_path.exists() and asset_path.exists() and not force:
        return {
            "version": version_id,
            "status": "already_downloaded",
            "runtime_path": str(runtime_path),
            "asset_path": str(asset_path),
            "metadata_path": str(metadata_path),
        }

    if not asset_path.exists() or force:
        request = Request(download_url, headers=HTTP_HEADERS)
        with urlopen(request) as response, NamedTemporaryFile(delete=False, dir=asset_dir) as tmp:
            shutil.copyfileobj(response, tmp)
            temp_path = Path(tmp.name)
        temp_path.replace(asset_path)
    extracted_member = extract_nvngx_dlss_from_zip(asset_path, runtime_path)

    metadata = {
        "version": version_id,
        "label": entry["label"],
        "source": entry.get("source"),
        "release_name": entry.get("release_name"),
        "release_url": entry.get("release_url"),
        "browser_download_url": download_url,
        "asset_name": entry.get("asset_name"),
        "asset_path": str(asset_path),
        "runtime_path": str(runtime_path),
        "extracted_member": extracted_member,
        "downloaded_at": utc_timestamp(),
    }
    atomic_write_json(metadata_path, metadata)

    return {
        "version": version_id,
        "status": "downloaded",
        "label": entry["label"],
        "asset_path": str(asset_path),
        "runtime_path": str(runtime_path),
        "metadata_path": str(metadata_path),
        "release_url": entry.get("release_url"),
        "browser_download_url": download_url,
    }
