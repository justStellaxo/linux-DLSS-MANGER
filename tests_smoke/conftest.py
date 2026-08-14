import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def run_cli():
    def _run(*args, **kwargs):
        return subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "main.py"), *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            **kwargs,
        )
    return _run


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app