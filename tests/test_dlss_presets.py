import pytest
from dlls_manager.launch_plan import build_profile_env_and_wrappers
from dlls_manager.profile_db import save_profile, load_profile


def _make_profile(tmp_project, **extra):
    base = {
        "enable_nvapi": True, "enable_smooth_motion": False,
        "use_gamemode": False, "use_mangohud": False,
        "launch_args": "", "custom_env": {},
        "dlss_mode": "game_default", "dlss_version": None,
        "allow_unsupported_override": False, "safety_mode": "strict",
        "dlss_sr_preset": None, "dlss_rr_preset": None,
        "dlss_fg_override": None, "enable_ngx_updater": False,
        "enable_hags": False, "enable_vkreflex": False,
        "proton_dlss_upgrade": None,
    }
    base.update(extra)
    save_profile("test", base)
    return load_profile("test")


class TestDlssPresetEnvVars:
    def test_sr_preset_generates_drs_settings(self, tmp_project):
        profile = _make_profile(tmp_project, dlss_sr_preset="latest")
        env, _ = build_profile_env_and_wrappers(profile)
        assert "DXVK_NVAPI_DRS_SETTINGS" in env
        assert "NGX_DLSS_SR_OVERRIDE=on" in env["DXVK_NVAPI_DRS_SETTINGS"]
        assert "render_preset_latest" in env["DXVK_NVAPI_DRS_SETTINGS"]

    def test_rr_and_sr_presets_generate_combined_drs(self, tmp_project):
        profile = _make_profile(tmp_project, dlss_sr_preset="j", dlss_rr_preset="k")
        env, _ = build_profile_env_and_wrappers(profile)
        drs = env["DXVK_NVAPI_DRS_SETTINGS"]
        assert "render_preset_j" in drs
        assert "render_preset_k" in drs

    def test_fg_override_on_adds_fg_to_drs(self, tmp_project):
        profile = _make_profile(tmp_project, dlss_fg_override="on")
        env, _ = build_profile_env_and_wrappers(profile)
        assert "NGX_DLSS_FG_OVERRIDE=on" in env["DXVK_NVAPI_DRS_SETTINGS"]

    def test_no_presets_no_drs_settings(self, tmp_project):
        profile = _make_profile(tmp_project)
        env, _ = build_profile_env_and_wrappers(profile)
        assert "DXVK_NVAPI_DRS_SETTINGS" not in env

    def test_hags_generates_winehags_env(self, tmp_project):
        profile = _make_profile(tmp_project, enable_hags=True)
        env, _ = build_profile_env_and_wrappers(profile)
        assert env.get("WINEHAGS") == "1"

    def test_vkreflex_generates_env(self, tmp_project):
        profile = _make_profile(tmp_project, enable_vkreflex=True)
        env, _ = build_profile_env_and_wrappers(profile)
        assert env.get("DXVK_NVAPI_VKREFLEX") == "1"

    def test_ngx_updater_generates_env(self, tmp_project):
        profile = _make_profile(tmp_project, enable_ngx_updater=True)
        env, _ = build_profile_env_and_wrappers(profile)
        assert env.get("PROTON_ENABLE_NGX_UPDATER") == "1"

    def test_proton_dlss_upgrade_env(self, tmp_project):
        profile = _make_profile(tmp_project, proton_dlss_upgrade="310.7")
        env, _ = build_profile_env_and_wrappers(profile)
        assert env.get("PROTON_DLSS_UPGRADE") == "310.7"


class TestProfileNewFields:
    def test_profile_accepts_new_preset_fields(self, tmp_project):
        save_profile("test", {
            "enable_nvapi": False, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
            "dlss_sr_preset": "j", "dlss_rr_preset": "latest",
            "dlss_fg_override": "on", "enable_ngx_updater": True,
            "enable_hags": True, "enable_vkreflex": True,
            "proton_dlss_upgrade": "1",
        })
        profile = load_profile("test")
        assert profile["dlss_sr_preset"] == "j"
        assert profile["dlss_rr_preset"] == "latest"
        assert profile["dlss_fg_override"] == "on"
        assert profile["enable_ngx_updater"] is True
        assert profile["enable_hags"] is True
        assert profile["enable_vkreflex"] is True
        assert profile["proton_dlss_upgrade"] == "1"

    def test_profile_defaults_new_fields_to_none_or_false(self, tmp_project):
        save_profile("minimal", {
            "enable_nvapi": False, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
        })
        profile = load_profile("minimal")
        assert profile["dlss_sr_preset"] is None
        assert profile["dlss_rr_preset"] is None
        assert profile["dlss_fg_override"] is None
        assert profile["enable_ngx_updater"] is False
        assert profile["enable_hags"] is False
        assert profile["enable_vkreflex"] is False
        assert profile["proton_dlss_upgrade"] is None