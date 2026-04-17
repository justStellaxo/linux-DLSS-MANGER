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


class CliPhase3Tests(unittest.TestCase):
    def test_profile_and_prepare_commands(self) -> None:
        listed = run_cli("list-profiles")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn("default", listed.stdout)

        shown = run_cli("show-install-override", "steam:sample-dx11")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        override = json.loads(shown.stdout)
        self.assertEqual(override["install_id"], "steam:sample-dx11")

        prepared = run_cli("prepare-launch", "--install-id", "steam:sample-dx11", "--profile", "default")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        payload = json.loads(prepared.stdout)
        self.assertIn("mutation_plan", payload)
        self.assertEqual(payload["install"]["id"], "steam:sample-dx11")
        self.assertEqual(payload["release_support"]["level"], "supported")
        self.assertEqual(payload["summary"]["install_id"], "steam:sample-dx11")

    def test_launch_dry_run_and_rollbacks_listing(self) -> None:
        launch = run_cli("launch", "--install-id", "steam:sample-dx11", "--profile", "default", "--dry-run")
        self.assertEqual(launch.returncode, 0, launch.stderr)
        payload = json.loads(launch.stdout)
        self.assertTrue(payload["ok"])
        self.assertIn("command", payload)
        self.assertEqual(payload["summary"]["release_support"], "supported")

        rollbacks = run_cli("list-rollbacks")
        self.assertEqual(rollbacks.returncode, 0, rollbacks.stderr)


if __name__ == "__main__":
    unittest.main()
