from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


AntiCheatPolicy = Literal["verified_supported", "warn", "blocked"]
AntiCheatLevel = Literal["none", "unknown", "low", "high"]
OverrideMode = Literal["native_only", "experimental", "blocked"]
SafetyMode = Literal["strict", "balanced", "unsafe"]
DiscoverySource = Literal[
    "steam",
    "faugus",
    "starcitizen_lug",
    "heroic",
    "lutris",
    "bottles",
    "desktop_entry",
    "manual",
]
LauncherFamily = Literal[
    "steam",
    "umu",
    "rsi",
    "heroic",
    "lutris",
    "bottles",
    "desktop",
    "native",
    "vendor_prefix_launcher",
    "manual",
]
StoreFamily = Literal[
    "steam",
    "battle.net",
    "rsi",
    "epic",
    "gog",
    "amazon",
    "ea",
    "ubisoft",
    "rockstar",
    "itch",
    "generic",
]
ExecutionStrategy = Literal[
    "steam_app",
    "steam_shortcut",
    "umu_game",
    "lutris_game",
    "bottles_program",
    "heroic_game",
    "legendary_game",
    "script_exec",
    "desktop_exec",
    "wine_exe",
    "native_exec",
]
ReleaseSupportLevel = Literal["supported", "advanced", "experimental"]

ANTI_CHEAT_POLICIES: set[AntiCheatPolicy] = {"verified_supported", "warn", "blocked"}
ANTI_CHEAT_LEVELS: set[AntiCheatLevel] = {"none", "unknown", "low", "high"}
OVERRIDE_MODES: set[OverrideMode] = {"native_only", "experimental", "blocked"}
SAFETY_MODES: set[SafetyMode] = {"strict", "balanced", "unsafe"}
DISCOVERY_SOURCES: set[DiscoverySource] = {
    "steam",
    "faugus",
    "starcitizen_lug",
    "heroic",
    "lutris",
    "bottles",
    "desktop_entry",
    "manual",
}
LAUNCHER_FAMILIES: set[LauncherFamily] = {
    "steam",
    "umu",
    "rsi",
    "heroic",
    "lutris",
    "bottles",
    "desktop",
    "native",
    "vendor_prefix_launcher",
    "manual",
}
STORE_FAMILIES: set[StoreFamily] = {
    "steam",
    "battle.net",
    "rsi",
    "epic",
    "gog",
    "amazon",
    "ea",
    "ubisoft",
    "rockstar",
    "itch",
    "generic",
}
EXECUTION_STRATEGIES: set[ExecutionStrategy] = {
    "steam_app",
    "steam_shortcut",
    "umu_game",
    "lutris_game",
    "bottles_program",
    "heroic_game",
    "legendary_game",
    "script_exec",
    "desktop_exec",
    "wine_exe",
    "native_exec",
}
RELEASE_SUPPORT_LEVELS: set[ReleaseSupportLevel] = {"supported", "advanced", "experimental"}


class GameRecord(TypedDict):
    id: str
    name: str
    launcher: str
    runtime: str
    anti_cheat: AntiCheatLevel
    anti_cheat_vendor: str | None
    anti_cheat_policy: AntiCheatPolicy
    supports_dlss_override: bool
    supports_dlss_version_selection: bool
    override_mode: OverrideMode
    notes: list[str]
    scan_path: str | None
    app_id: NotRequired[str]


class Profile(TypedDict):
    enable_nvapi: bool
    enable_smooth_motion: bool
    use_gamemode: bool
    use_mangohud: bool
    launch_args: str
    custom_env: dict[str, str]
    dlss_mode: str
    dlss_version: str | None
    allow_unsupported_override: bool
    safety_mode: SafetyMode


class InstallOverride(TypedDict):
    install_id: str
    extra_env: dict[str, str]
    extra_wrappers: list[str]
    launch_args: str
    dlss_version: str | None
    enable_nvapi: bool | None
    enable_smooth_motion: bool | None
    use_gamemode: bool | None
    use_mangohud: bool | None
    allow_unsupported_override: bool | None
    sync_to_launcher: bool
    dlss_target_path: str | None
    notes: list[str]


class LauncherInstallRecord(TypedDict):
    id: str
    display_name: str
    source: DiscoverySource
    source_id: str
    launcher_family: LauncherFamily
    store_family: StoreFamily
    execution_strategy: ExecutionStrategy
    runtime: str
    install_root: str | None
    prefix_path: str | None
    runner_name: str | None
    runner_path: str | None
    exe_path: str | None
    script_path: str | None
    desktop_file: str | None
    app_id: str | None
    launch_command: list[str]
    launch_env: dict[str, str]
    launch_args: str
    wrapper_chain: list[str]
    working_directory: str | None
    scan_paths: list[str]
    notes: list[str]
    validation_errors: list[str]
    validation_warnings: list[str]
    discovery_confidence: str
    anti_cheat: AntiCheatLevel
    anti_cheat_vendor: str | None
    anti_cheat_policy: AntiCheatPolicy
    supports_dlss_override: bool
    supports_dlss_version_selection: bool
    override_mode: OverrideMode


class AntiCheatRule(TypedDict):
    vendor: str
    markers: list[str]
    default_policy: AntiCheatPolicy
    anti_cheat_level: AntiCheatLevel
    notes: str


class DlssVersionRecord(TypedDict):
    id: str
    label: str
    selectable: bool


class MarkerHit(TypedDict):
    vendor: str
    marker: str
    default_policy: AntiCheatPolicy
    anti_cheat_level: AntiCheatLevel
    notes: str


class AntiCheatAssessment(TypedDict):
    vendor: str | None
    confidence: str
    policy: AntiCheatPolicy
    anti_cheat_level: AntiCheatLevel
    reasons: list[str]
    marker_hits: list[MarkerHit]
    safe_actions: list[str]
    blocked_actions: list[str]


class DlssPolicyEvaluation(TypedDict):
    selected_version: str | None
    warnings: list[str]
    blocked_reasons: list[str]


class ExecutionPlan(TypedDict):
    executable: list[str]
    env: dict[str, str]
    wrappers: list[str]
    args: str
    working_directory: str | None
    command_preview: str


class ValidationResult(TypedDict):
    install_id: str
    ok: bool
    errors: list[str]
    warnings: list[str]
    release_support: ReleaseSupportStatus
    summary: ResultSummary


class DiscoveryReport(TypedDict):
    created_at: str
    installs: list[LauncherInstallRecord]
    warnings: list[str]


class MutationStep(TypedDict):
    id: str
    action: str
    description: str
    source_path: str | None
    target_path: str
    payload: dict | str | None
    backup_required: bool


class MutationPlan(TypedDict):
    install_id: str
    profile: str
    override: InstallOverride
    created_at: str
    status: str
    steps: list[MutationStep]
    warnings: list[str]
    blocked_reasons: list[str]
    compatibility_status: str


class RollbackFileRecord(TypedDict):
    target_path: str
    backup_path: str | None
    existed_before: bool
    action: str


class ReleaseSupportStatus(TypedDict):
    level: ReleaseSupportLevel
    note: str


class ResultSummary(TypedDict):
    install_id: str | None
    display_name: str | None
    profile: str | None
    release_support: ReleaseSupportLevel | None
    compatibility_status: str | None
    warning_count: int
    error_count: int
    blocked: bool


class RollbackRecord(TypedDict):
    rollback_id: str
    install_id: str
    profile: str
    created_at: str
    files: list[RollbackFileRecord]
    launcher_sync_paths: list[str]
    metadata: dict


class ApplyResult(TypedDict):
    ok: bool
    rollback_id: str | None
    applied_steps: list[str]
    errors: list[str]
    warnings: list[str]
    summary: ResultSummary | None
    plan: MutationPlan


class PreparedLaunch(TypedDict):
    install: LauncherInstallRecord
    profile: str
    effective_profile: Profile
    override: InstallOverride
    launch_plan: dict
    mutation_plan: MutationPlan
    execution: ExecutionPlan
    release_support: ReleaseSupportStatus
    summary: ResultSummary


class LaunchResult(TypedDict):
    ok: bool
    pid: int | None
    returncode: int | None
    command: list[str]
    applied: ApplyResult | None
    errors: list[str]
    warnings: list[str]
    summary: ResultSummary | None


class LaunchPlan(TypedDict):
    game: GameRecord
    profile: str
    env: dict[str, str]
    wrappers: list[str]
    args: str
    command_preview: str
    anti_cheat_assessment: dict[str, str | None]
    policy_reasons: list[str]
    marker_hits: list[MarkerHit]
    dlss_version_selection: str | None
    requested_features: list[str]
    compatibility_status: str
    warnings: list[str]
    blocked_reasons: list[str]
    notes: list[str]


class InstallLaunchPlan(TypedDict):
    install: LauncherInstallRecord
    profile: str
    base_profile_config: Profile
    effective_profile_config: Profile
    override: InstallOverride
    env: dict[str, str]
    wrappers: list[str]
    args: str
    command_preview: str
    anti_cheat_assessment: dict[str, str | None]
    policy_reasons: list[str]
    marker_hits: list[MarkerHit]
    dlss_version_selection: str | None
    requested_features: list[str]
    compatibility_status: str
    warnings: list[str]
    blocked_reasons: list[str]
    mutation_plan: MutationPlan
    release_support: ReleaseSupportStatus
    notes: list[str]


class SnapshotRecord(TypedDict):
    command: str
    created_at: str
    tool_version: str
    summary: dict
    payload: dict
