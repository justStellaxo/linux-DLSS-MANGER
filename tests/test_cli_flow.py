import json
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "main.py", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class CliFlowTests(unittest.TestCase):
    def test_discover_and_list_installs(self) -> None:
        discover = run_cli("discover-launchers")
        self.assertEqual(discover.returncode, 0, discover.stderr)
        payload = json.loads(discover.stdout)
        self.assertTrue(payload["installs"])

        listed = run_cli("list-installs")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn("steam:sample-dx11", listed.stdout)
        self.assertIn("support=supported", listed.stdout)

    def test_show_and_validate_install(self) -> None:
        run_cli("discover-launchers")
        shown = run_cli("show-install", "steam:sample-dx11")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        install = json.loads(shown.stdout)
        self.assertEqual(install["id"], "steam:sample-dx11")

        validated = run_cli("validate-install", "steam:sample-dx11")
        self.assertEqual(validated.returncode, 0, validated.stderr)
        report = json.loads(validated.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["release_support"]["level"], "supported")
        self.assertEqual(report["summary"]["compatibility_status"], "ok")

    def test_launch_preview_default_ok(self) -> None:
        result = run_cli("launch-preview", "sample-dx11", "--profile", "default")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["compatibility_status"], "ok")
        self.assertEqual(payload["anti_cheat_assessment"]["policy"], "verified_supported")
        self.assertEqual(
            payload["command_preview"],
            "DXVK_ENABLE_NVAPI=1 DXVK_HUD=0 PROTON_ENABLE_NVAPI=1 gamemoderun mangohud steam -applaunch 123456",
        )

    def test_launch_preview_install_id(self) -> None:
        run_cli("discover-launchers")
        result = run_cli("launch-preview", "--install-id", "steam:sample-dx11", "--profile", "default")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["compatibility_status"], "ok")
        self.assertEqual(payload["install"]["id"], "steam:sample-dx11")
        self.assertEqual(payload["release_support"]["level"], "supported")

    def test_explain_policy_blocks_experimental_eac_title(self) -> None:
        result = run_cli("explain-policy", "sample-dx12", "--profile", "experimental")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["compatibility_status"], "blocked")
        self.assertTrue(payload["blocked_reasons"])

    def test_export_mock_ui_data(self) -> None:
        result = run_cli("export-mock-ui-data")
        self.assertEqual(result.returncode, 0, result.stderr)
        exported = PROJECT_ROOT / "mock_ui" / "mock-library.json"
        exported_script = PROJECT_ROOT / "mock_ui" / "mock-library.js"
        self.assertTrue(exported.exists())
        self.assertTrue(exported_script.exists())
        payload = json.loads(exported.read_text(encoding="utf-8"))
        self.assertTrue(payload["games"])
        self.assertIn("capabilities", payload)
        self.assertIn("profiles", payload["games"][0])


if __name__ == "__main__":
    unittest.main()
