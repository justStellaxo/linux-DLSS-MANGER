import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return (result.stdout or result.stderr).strip()
    except Exception as exc:
        return f"Error running {' '.join(cmd)}: {exc}"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, dump_json(payload))


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_process_running(names: set[str]) -> bool:
    proc_root = Path("/proc")
    if not proc_root.exists():
        return False

    wanted = {name.strip().lower() for name in names if name.strip()}
    if not wanted:
        return False

    for comm_path in proc_root.glob("[0-9]*/comm"):
        try:
            process_name = comm_path.read_text(encoding="utf-8").strip().lower()
        except OSError:
            continue
        if process_name in wanted:
            return True
    return False
