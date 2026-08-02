#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from src.config import Config, load_config
from src.manifest import open_manifest
from src.organizer import run_pipeline
from src.review import resolve_review_item, write_review_manifest_csv

log = logging.getLogger("photo_organizer")


def _cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)

    drive_service = None
    if args.source in ("drive", "all") and config.drive_source_folders:
        from src.drive_client import build_drive_service

        drive_service = build_drive_service(config)
    elif args.source in ("drive", "all"):
        log.info("No drive_source_folders configured -- skipping Google Drive sync.")

    with open_manifest(config.manifest_path) as manifest:
        report = run_pipeline(
            config, manifest, drive_service=drive_service, source=args.source, dry_run=args.dry_run
        )
        if not args.dry_run:
            write_review_manifest_csv(config, manifest)

    print(f"{'[dry-run] ' if args.dry_run else ''}organized: {report.count('organized')}")
    print(f"{'[dry-run] ' if args.dry_run else ''}review:    {report.count('review')}")
    print(f"{'[dry-run] ' if args.dry_run else ''}duplicate: {report.count('duplicate')}")

    if args.report:
        import csv

        with open(args.report, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["original_name", "origin", "action", "dest_path", "confidence", "source_tag"])
            for e in report.entries:
                writer.writerow(
                    [
                        e.record.original_name,
                        e.record.origin,
                        e.action,
                        str(e.dest_path) if e.dest_path else "",
                        e.resolution.confidence.value if e.resolution else "",
                        e.resolution.source_tag if e.resolution else "",
                    ]
                )
        print(f"Report written to {args.report}")

    return 0


def _cmd_review_list(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    with open_manifest(config.manifest_path) as manifest:
        rows = manifest.list_by_status("review")
        csv_path = write_review_manifest_csv(config, manifest)
    print(f"{len(rows)} photo(s) awaiting review. See {csv_path}")
    for row in rows:
        print(f"  {row['sha256'][:12]}  {row['source_tag']:<28} {row['dest_path']}")
    return 0


def _cmd_review_resolve(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    try:
        manual_date = datetime.strptime(args.date, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print(f"--date must be in 'YYYY-MM-DD HH:MM:SS' format, got: {args.date}", file=sys.stderr)
        return 1

    with open_manifest(config.manifest_path) as manifest:
        try:
            dest = resolve_review_item(config, manifest, args.sha256, manual_date)
        except (ValueError, FileNotFoundError) as e:
            print(str(e), file=sys.stderr)
            return 1
        write_review_manifest_csv(config, manifest)
    print(f"Organized into {dest}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    with open_manifest(config.manifest_path) as manifest:
        counts = manifest.counts_by_status()
    print(f"organized: {counts.get('organized', 0)}")
    print(f"review:    {counts.get('review', 0)}")
    return 0


def _cmd_auth(args: argparse.Namespace) -> int:
    from src.drive_client import get_credentials

    config = load_config(args.config)
    get_credentials(config)
    print(f"OAuth token cached at {config.token_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    # --config/-v are defined on this shared parent so they work both before AND after
    # the subcommand (e.g. both `run --config x.yaml` and `--config x.yaml run` parse).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    common.add_argument("-v", "--verbose", action="store_true")

    parser = argparse.ArgumentParser(prog="organize_photos.py", parents=[common])
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Sync sources and organize photos (default)", parents=[common])
    run_p.add_argument("--dry-run", action="store_true", help="Preview only, write nothing")
    run_p.add_argument("--source", choices=["drive", "naver", "all"], default="all")
    run_p.add_argument("--report", help="Write a CSV plan/summary to this path")
    run_p.set_defaults(func=_cmd_run)

    review_p = sub.add_parser("review", help="Manage low-confidence photos", parents=[common])
    review_sub = review_p.add_subparsers(dest="review_command", required=True)

    review_list_p = review_sub.add_parser("list", help="List photos awaiting review", parents=[common])
    review_list_p.set_defaults(func=_cmd_review_list)

    review_resolve_p = review_sub.add_parser("resolve", help="Manually confirm a date", parents=[common])
    review_resolve_p.add_argument("--sha256", required=True)
    review_resolve_p.add_argument("--date", required=True, help="'YYYY-MM-DD HH:MM:SS'")
    review_resolve_p.set_defaults(func=_cmd_review_resolve)

    status_p = sub.add_parser("status", help="Summary of organized/review counts", parents=[common])
    status_p.set_defaults(func=_cmd_status)

    auth_p = sub.add_parser("auth", help="Run the one-time Google OAuth handshake", parents=[common])
    auth_p.set_defaults(func=_cmd_auth)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    if not args.command:
        args.command = "run"
        args.func = _cmd_run
        args.dry_run = False
        args.source = "all"
        args.report = None

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
