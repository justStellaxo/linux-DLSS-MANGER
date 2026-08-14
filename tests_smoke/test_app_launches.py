import importlib
import ast
from pathlib import Path


class TestAppImports:
    def test_import_cli(self):
        importlib.import_module("dlls_manager.cli")

    def test_import_gui_main(self):
        importlib.import_module("dlls_manager.gui.__main__")

    def test_import_gui_main_window(self):
        importlib.import_module("dlls_manager.gui.main_window")

    def test_import_all_pages(self):
        for page in ["library", "catalog", "profiles", "rollbacks", "system"]:
            importlib.import_module(f"dlls_manager.gui.pages.{page}")

    def test_import_workers(self):
        importlib.import_module("dlls_manager.gui.workers")

    def test_no_fastapi_imports_remain(self):
        root = Path(__file__).resolve().parent.parent / "dlls_manager"
        for py_file in root.rglob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "fastapi" not in alias.name.lower(), f"FastAPI import found in {py_file}"
                if isinstance(node, ast.ImportFrom):
                    assert "fastapi" not in (node.module or "").lower(), f"FastAPI import found in {py_file}"