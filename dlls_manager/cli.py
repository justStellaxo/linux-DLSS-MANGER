import argparse

from dlls_manager.dlss_catalog import (
    download_dlss_version,
    get_dlss_version,
    load_dlss_versions,
    refresh_dlss_catalog,
)
from dlls_manager.detector import detect_capabilities
from dlls_manager.install_db import discover_and_cache_installs, get_install, validate_install
from dlls_manager.launcher_runtime import apply_install_plan, launch_install, prepare_launch
from dlls_manager.launch_plan import (
    build_install_launch_plan,
    build_launch_plan,
    explain_install_policy,
    explain_policy,
    list_games_summary,
    list_installs_summary,
)
from dlls_manager.mock_data import build_mock_ui_script, export_mock_library
from dlls_manager.mutations import list_rollbacks, load_rollback_record, rollback_mutation
from dlls_manager.override_db import load_install_override, update_install_override
from dlls_manager.paths import MOCK_UI_DATA_FILE, MOCK_UI_SCRIPT_FILE
from dlls_manager.profile_db import list_profiles, load_profile, update_profile
from dlls_manager.snapshots import write_snapshot
from dlls_manager.utils import dump_json


def _parse_set_pairs(values: list[str] | None) -> dict[str, str]:
    updates: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise SystemExit(f"Expected key=value pair, got: {item}")
        key, value = item.split("=", 1)
        updates[key] = value
    return updates


def cmd_detect(args: argparse.Namespace) -> None:
    report = detect_capabilities()
    if args.snapshot:
        report["snapshot_path"] = write_snapshot("detect", report)
    print(dump_json(report))


def cmd_list_games(_: argparse.Namespace) -> None:
    for game in list_games_summary():
        vendor = game["anti_cheat_vendor"] or "n/a"
        print(
            f"- {game['id']}: {game['name']} ({game['launcher']}) "
            f"[runtime={game['runtime']}, anti-cheat={game['anti_cheat_level']}, "
            f"policy={game['anti_cheat_policy']}, vendor={vendor}, confidence={game['anti_cheat_confidence']}]"
        )


def cmd_launch_preview(args: argparse.Namespace) -> None:
    if args.install_id:
        plan = build_install_launch_plan(args.install_id, args.profile)
    else:
        if not args.game_id:
            raise SystemExit("launch-preview requires either a game_id or --install-id")
        plan = build_launch_plan(args.game_id, args.profile)
    if args.snapshot:
        plan["snapshot_path"] = write_snapshot("preview", plan)
    print(dump_json(plan))


def cmd_explain_policy(args: argparse.Namespace) -> None:
    if args.install_id:
        report = explain_install_policy(args.install_id, args.profile)
    else:
        if not args.game_id:
            raise SystemExit("explain-policy requires either a game_id or --install-id")
        report = explain_policy(args.game_id, args.profile)
    if args.snapshot:
        report["snapshot_path"] = write_snapshot("policy", report)
    print(dump_json(report))


def cmd_discover_launchers(args: argparse.Namespace) -> None:
    report = discover_and_cache_installs()
    if args.snapshot:
        report["snapshot_path"] = write_snapshot("discovery", report)
    print(dump_json(report))


def cmd_list_installs(args: argparse.Namespace) -> None:
    for install in list_installs_summary(refresh=args.refresh):
        vendor = install["anti_cheat_vendor"] or "n/a"
        print(
            f"- {install['id']}: {install['name']} "
            f"[source={install['source']}, launcher={install['launcher_family']}, store={install['store_family']}, "
            f"runtime={install['runtime']}, support={install['release_support']}, "
            f"policy={install['anti_cheat_policy']}, vendor={vendor}, "
            f"errors={len(install['validation_errors'])}, warnings={len(install['validation_warnings'])}]"
        )


def cmd_show_install(args: argparse.Namespace) -> None:
    install = get_install(args.install_id, refresh=args.refresh)
    print(dump_json(install))


def cmd_validate_install(args: argparse.Namespace) -> None:
    report = validate_install(args.install_id, refresh=args.refresh)
    if args.snapshot:
        report["snapshot_path"] = write_snapshot("validation", report)
    print(dump_json(report))


def cmd_export_mock_ui_data(args: argparse.Namespace) -> None:
    payload = export_mock_library(refresh_catalog=not args.skip_catalog_refresh)
    MOCK_UI_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    MOCK_UI_DATA_FILE.write_text(dump_json(payload), encoding="utf-8")
    MOCK_UI_SCRIPT_FILE.write_text(build_mock_ui_script(payload), encoding="utf-8")
    if args.snapshot:
        payload["snapshot_path"] = write_snapshot("mock-ui", payload)
        MOCK_UI_DATA_FILE.write_text(dump_json(payload), encoding="utf-8")
        MOCK_UI_SCRIPT_FILE.write_text(build_mock_ui_script(payload), encoding="utf-8")
    print(f"Wrote mock UI data to {MOCK_UI_DATA_FILE} and {MOCK_UI_SCRIPT_FILE}")


def cmd_refresh_dlss_catalog(_: argparse.Namespace) -> None:
    print(dump_json(refresh_dlss_catalog()))


def cmd_list_dlss_catalog(_: argparse.Namespace) -> None:
    for entry in load_dlss_versions():
        if entry["id"] == "game_default":
            print(f"- {entry['id']}: {entry['label']} [selectable={entry['selectable']}]")
            continue
        print(
            f"- {entry['id']}: {entry['label']} "
            f"[published_at={entry.get('published_at', 'n/a')}, downloaded={entry.get('downloaded', False)}, "
            f"asset={entry.get('asset_name', 'n/a')}]"
        )


def cmd_show_dlss_version(args: argparse.Namespace) -> None:
    print(dump_json(get_dlss_version(args.version_id)))


def cmd_download_dlss(args: argparse.Namespace) -> None:
    print(dump_json(download_dlss_version(args.version_id, force=args.force)))


def cmd_list_profiles(_: argparse.Namespace) -> None:
    for profile_name in list_profiles():
        print(f"- {profile_name}")


def cmd_show_profile(args: argparse.Namespace) -> None:
    print(dump_json(load_profile(args.profile_name)))


def cmd_update_profile(args: argparse.Namespace) -> None:
    updated = update_profile(args.profile_name, _parse_set_pairs(args.set_values))
    if args.snapshot:
        payload = dict(updated)
        payload["snapshot_path"] = write_snapshot("profile-update", payload)
        print(dump_json(payload))
        return
    print(dump_json(updated))


def cmd_show_install_override(args: argparse.Namespace) -> None:
    print(dump_json(load_install_override(args.install_id)))


def cmd_update_install_override(args: argparse.Namespace) -> None:
    updated = update_install_override(args.install_id, _parse_set_pairs(args.set_values))
    if args.snapshot:
        payload = dict(updated)
        payload["snapshot_path"] = write_snapshot("override-update", payload)
        print(dump_json(payload))
        return
    print(dump_json(updated))


def cmd_prepare_launch(args: argparse.Namespace) -> None:
    payload = prepare_launch(args.install_id, args.profile)
    if args.snapshot:
        payload["snapshot_path"] = write_snapshot("prepare-launch", payload)
    print(dump_json(payload))


def cmd_apply(args: argparse.Namespace) -> None:
    payload = apply_install_plan(args.install_id, args.profile, force=args.force)
    if args.snapshot:
        payload["snapshot_path"] = write_snapshot("apply", payload)
    print(dump_json(payload))


def cmd_launch(args: argparse.Namespace) -> None:
    payload = launch_install(
        args.install_id,
        args.profile,
        dry_run=args.dry_run,
        wait=args.wait,
        force=args.force,
    )
    if args.snapshot:
        payload["snapshot_path"] = write_snapshot("launch", payload)
    print(dump_json(payload))


def cmd_list_rollbacks(_: argparse.Namespace) -> None:
    for entry in list_rollbacks():
        print(
            f"- {entry['rollback_id']}: {entry['install_id']} "
            f"[profile={entry['profile']}, created_at={entry['created_at']}, files={entry['files']}]"
        )


def cmd_show_rollback(args: argparse.Namespace) -> None:
    print(dump_json(load_rollback_record(args.rollback_id)))


def cmd_rollback(args: argparse.Namespace) -> None:
    payload = rollback_mutation(args.rollback_id)
    if args.snapshot:
        payload["snapshot_path"] = write_snapshot("rollback", payload)
    print(dump_json(payload))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Linux DLSS Manager prototype CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    detect = sub.add_parser("detect", help="Print system capability report")
    detect.add_argument("--snapshot", action="store_true", help="Persist report to snapshots/")
    detect.set_defaults(func=cmd_detect)

    list_games = sub.add_parser("list-games", help="List known games from games.json")
    list_games.set_defaults(func=cmd_list_games)

    discover = sub.add_parser("discover-launchers", help="Discover local launcher/game installations")
    discover.add_argument("--refresh", action="store_true", help="Force a fresh discovery scan")
    discover.add_argument("--snapshot", action="store_true", help="Persist discovery report to snapshots/")
    discover.set_defaults(func=cmd_discover_launchers)

    list_installs = sub.add_parser("list-installs", help="List discovered launcher/game installations")
    list_installs.add_argument("--refresh", action="store_true", help="Force a fresh discovery scan before listing")
    list_installs.set_defaults(func=cmd_list_installs)

    show_install = sub.add_parser("show-install", help="Show a discovered installation record")
    show_install.add_argument("install_id", help="Installation ID from discover-launchers")
    show_install.add_argument("--refresh", action="store_true", help="Force a fresh discovery scan before loading")
    show_install.set_defaults(func=cmd_show_install)

    validate = sub.add_parser("validate-install", help="Validate a discovered installation record")
    validate.add_argument("install_id", help="Installation ID from discover-launchers")
    validate.add_argument("--refresh", action="store_true", help="Force a fresh discovery scan before validating")
    validate.add_argument("--snapshot", action="store_true", help="Persist validation report to snapshots/")
    validate.set_defaults(func=cmd_validate_install)

    preview = sub.add_parser("launch-preview", help="Build and print launch plan")
    preview.add_argument("game_id", nargs="?", help="Game ID from games.json")
    preview.add_argument("--install-id", help="Installation ID from discover-launchers")
    preview.add_argument("--profile", default="default", help="Profile name from profiles/<name>.json")
    preview.add_argument("--snapshot", action="store_true", help="Persist launch plan to snapshots/")
    preview.set_defaults(func=cmd_launch_preview)

    explain = sub.add_parser("explain-policy", help="Explain anti-cheat and DLSS policy decisions")
    explain.add_argument("game_id", nargs="?", help="Game ID from games.json")
    explain.add_argument("--install-id", help="Installation ID from discover-launchers")
    explain.add_argument("--profile", default="default", help="Profile name from profiles/<name>.json")
    explain.add_argument("--snapshot", action="store_true", help="Persist policy report to snapshots/")
    explain.set_defaults(func=cmd_explain_policy)

    export = sub.add_parser("export-mock-ui-data", help="Export planner data for the static mock UI")
    export.add_argument(
        "--skip-catalog-refresh",
        action="store_true",
        help="Use the local DLSS catalog as-is without refreshing official NVIDIA releases first",
    )
    export.add_argument("--snapshot", action="store_true", help="Persist export metadata to snapshots/")
    export.set_defaults(func=cmd_export_mock_ui_data)

    refresh_dlss = sub.add_parser("refresh-dlss-catalog", help="Refresh dlss_versions.json from official NVIDIA releases")
    refresh_dlss.set_defaults(func=cmd_refresh_dlss_catalog)

    list_dlss = sub.add_parser("list-dlss-catalog", help="List known DLSS catalog entries")
    list_dlss.set_defaults(func=cmd_list_dlss_catalog)

    show_dlss = sub.add_parser("show-dlss-version", help="Show one DLSS catalog entry")
    show_dlss.add_argument("version_id", help="DLSS version id such as 3.7.10")
    show_dlss.set_defaults(func=cmd_show_dlss_version)

    download_dlss = sub.add_parser("download-dlss", help="Download and extract one official DLSS runtime")
    download_dlss.add_argument("version_id", help="DLSS version id such as 3.7.10")
    download_dlss.add_argument("--force", action="store_true", help="Redownload even if the runtime is already present")
    download_dlss.set_defaults(func=cmd_download_dlss)

    list_profiles_parser = sub.add_parser("list-profiles", help="List stored profile names")
    list_profiles_parser.set_defaults(func=cmd_list_profiles)

    show_profile = sub.add_parser("show-profile", help="Show a stored profile")
    show_profile.add_argument("profile_name", help="Profile name from profiles/<name>.json")
    show_profile.set_defaults(func=cmd_show_profile)

    update_profile_parser = sub.add_parser("update-profile", help="Update and persist a profile")
    update_profile_parser.add_argument("profile_name", help="Profile name from profiles/<name>.json")
    update_profile_parser.add_argument("--set", dest="set_values", action="append", help="Update value as key=value", required=True)
    update_profile_parser.add_argument("--snapshot", action="store_true", help="Persist update report to snapshots/")
    update_profile_parser.set_defaults(func=cmd_update_profile)

    show_override = sub.add_parser("show-install-override", help="Show persisted install override state")
    show_override.add_argument("install_id", help="Installation ID from discover-launchers")
    show_override.set_defaults(func=cmd_show_install_override)

    update_override = sub.add_parser("update-install-override", help="Update and persist install override state")
    update_override.add_argument("install_id", help="Installation ID from discover-launchers")
    update_override.add_argument("--set", dest="set_values", action="append", help="Update value as key=value", required=True)
    update_override.add_argument("--snapshot", action="store_true", help="Persist update report to snapshots/")
    update_override.set_defaults(func=cmd_update_install_override)

    prepare = sub.add_parser("prepare-launch", help="Resolve launch, apply, and mutation data for an install")
    prepare.add_argument("--install-id", required=True, help="Installation ID from discover-launchers")
    prepare.add_argument("--profile", default="default", help="Profile name from profiles/<name>.json")
    prepare.add_argument("--snapshot", action="store_true", help="Persist prepare report to snapshots/")
    prepare.set_defaults(func=cmd_prepare_launch)

    apply_parser = sub.add_parser("apply", help="Apply planned file and launcher mutations")
    apply_parser.add_argument("--install-id", required=True, help="Installation ID from discover-launchers")
    apply_parser.add_argument("--profile", default="default", help="Profile name from profiles/<name>.json")
    apply_parser.add_argument("--force", action="store_true", help="Apply even if the policy path is blocked")
    apply_parser.add_argument("--snapshot", action="store_true", help="Persist apply report to snapshots/")
    apply_parser.set_defaults(func=cmd_apply)

    launch = sub.add_parser("launch", help="Apply planned changes and launch the install")
    launch.add_argument("--install-id", required=True, help="Installation ID from discover-launchers")
    launch.add_argument("--profile", default="default", help="Profile name from profiles/<name>.json")
    launch.add_argument("--dry-run", action="store_true", help="Resolve apply and execution without starting the process")
    launch.add_argument("--wait", action="store_true", help="Wait for the process and capture the exit code")
    launch.add_argument("--force", action="store_true", help="Launch even if the policy path is blocked")
    launch.add_argument("--snapshot", action="store_true", help="Persist launch report to snapshots/")
    launch.set_defaults(func=cmd_launch)

    list_rollbacks_parser = sub.add_parser("list-rollbacks", help="List stored rollback manifests")
    list_rollbacks_parser.set_defaults(func=cmd_list_rollbacks)

    show_rollback = sub.add_parser("show-rollback", help="Show a rollback manifest")
    show_rollback.add_argument("rollback_id", help="Rollback identifier from list-rollbacks")
    show_rollback.set_defaults(func=cmd_show_rollback)

    rollback = sub.add_parser("rollback", help="Restore files from a rollback manifest")
    rollback.add_argument("rollback_id", help="Rollback identifier from list-rollbacks")
    rollback.add_argument("--snapshot", action="store_true", help="Persist rollback report to snapshots/")
    rollback.set_defaults(func=cmd_rollback)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
