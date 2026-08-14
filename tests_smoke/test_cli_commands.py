import json


class TestCliSmoke:
    def test_help_exits_zero(self, run_cli):
        result = run_cli("--help")
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()

    def test_detect(self, run_cli):
        result = run_cli("detect")
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert "os" in payload
        assert "python" in payload

    def test_list_profiles(self, run_cli):
        result = run_cli("list-profiles")
        assert result.returncode == 0

    def test_list_dlss_catalog(self, run_cli):
        result = run_cli("list-dlss-catalog")
        assert result.returncode == 0

    def test_list_installs(self, run_cli):
        result = run_cli("list-installs")
        assert result.returncode == 0

    def test_serve_ui_command_removed(self, run_cli):
        result = run_cli("serve-ui")
        assert result.returncode != 0

    def test_export_mock_ui_command_removed(self, run_cli):
        result = run_cli("export-mock-ui-data")
        assert result.returncode != 0