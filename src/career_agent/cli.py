"""Command-line entry point for the FoxPilot pipeline."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from .config import DEFAULT_DATA_DIR, LEGACY_DATA_DIR, load_config
from .storage import JobStore

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="foxpilot",
        description="Local-first job discovery and career decision support.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Create local FoxPilot configuration.",
    )
    init_parser.add_argument(
        "--resume",
        type=Path,
        help="Optional local resume path.",
    )
    init_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Local data directory (default: {DEFAULT_DATA_DIR}).",
    )
    init_parser.add_argument(
        "--provider",
        choices=("ollama", "openai"),
        help="LLM provider to use (default: ollama).",
    )
    init_parser.add_argument(
        "--model",
        help="LLM model name (default: llama3.1:8b).",
    )

    scan_parser = subparsers.add_parser(
        "scan",
        help="Run the current job discovery and matching pipeline.",
    )
    scan_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate local setup without starting the browser pipeline.",
    )

    subparsers.add_parser(
        "migrate",
        help="Import legacy JSON jobs into the local SQLite database.",
    )

    return parser


def init_project(args: argparse.Namespace) -> int:
    data_dir = args.data_dir.expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    config_path = data_dir / "config.json"

    config = {
        "data_dir": str(data_dir),
        "resume_path": str(args.resume.expanduser().resolve()) if args.resume else None,
        "llm_provider": args.provider or os.getenv("LLM_PROVIDER", "ollama"),
        "llm_model": args.model or os.getenv("LLM_MODEL", "llama3.1:8b"),
        "target_roles": [],
        "locations": [],
    }

    if config_path.exists():
        if not args.resume and not args.provider and not args.model:
            print(f"Configuration already exists: {config_path}")
            return 0
        existing = json.loads(config_path.read_text(encoding="utf-8"))
        if args.resume:
            existing["resume_path"] = str(args.resume.expanduser().resolve())
        if args.provider:
            existing["llm_provider"] = args.provider
        if args.model:
            existing["llm_model"] = args.model
        config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        print(f"FoxPilot configuration updated: {config_path}")
        return 0

    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"FoxPilot initialized: {config_path}")
    print("Next: configure target_roles and locations, then run `foxpilot scan`.")
    return 0


def scan_project(args: argparse.Namespace) -> int:
    if args.dry_run:
        print(f"Repository: {REPOSITORY_ROOT}")
        print(f"Python: {sys.executable}")
        print("Dry run passed. The browser pipeline was not started.")
        return 0

    pipeline = REPOSITORY_ROOT / "src" / "run_agent.py"
    if not pipeline.exists():
        print(f"Pipeline entry point not found: {pipeline}", file=sys.stderr)
        return 1

    result = subprocess.run(
        [sys.executable, str(pipeline)],
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    return result.returncode


def migrate_project() -> int:
    target_dir = DEFAULT_DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target_database = target_dir / "foxpilot.sqlite3"
    legacy_database = LEGACY_DATA_DIR / "career_agent.sqlite3"
    legacy_profile = LEGACY_DATA_DIR / "career_profile.json"

    if legacy_database.exists() and not target_database.exists():
        source = sqlite3.connect(legacy_database)
        destination = sqlite3.connect(target_database)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        print(f"Migrated legacy database to {target_database}")

    target_profile = target_dir / "career_profile.json"
    if legacy_profile.exists() and not target_profile.exists():
        shutil.copy2(legacy_profile, target_profile)
        print(f"Migrated legacy profile to {target_profile}")

    config = load_config(DEFAULT_DATA_DIR / "config.json")
    with JobStore(config.database_path) as store:
        imported = store.import_legacy_jobs(REPOSITORY_ROOT / "data" / "jobs")
    print(f"Imported {imported} legacy job record(s) into {config.database_path}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "init":
        return init_project(args)
    if args.command == "scan":
        return scan_project(args)
    if args.command == "migrate":
        return migrate_project()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
