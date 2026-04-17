from datetime import datetime, timezone

from dlls_manager import __version__
from dlls_manager.models import SnapshotRecord
from dlls_manager.paths import SNAPSHOTS_DIR
from dlls_manager.utils import dump_json


def _snapshot_summary(payload: dict) -> dict:
    install_like = payload.get("install") if isinstance(payload.get("install"), dict) else None
    release_support = payload.get("release_support") if isinstance(payload.get("release_support"), dict) else None
    result_summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else None
    return {
        "install_id": payload.get("install_id") or (install_like or {}).get("id"),
        "profile": payload.get("profile"),
        "compatibility_status": payload.get("compatibility_status"),
        "release_support": (release_support or {}).get("level"),
        "result_summary": result_summary,
    }


def build_snapshot_record(command: str, payload: dict, timestamp: str) -> SnapshotRecord:
    return {
        "command": command,
        "created_at": timestamp,
        "tool_version": __version__,
        "summary": _snapshot_summary(payload),
        "payload": payload,
    }


def write_snapshot(command: str, payload: dict) -> str:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    path = SNAPSHOTS_DIR / f"{command}-{timestamp}.json"
    wrapped = build_snapshot_record(command, payload, timestamp)
    path.write_text(dump_json(wrapped), encoding="utf-8")
    return str(path)
