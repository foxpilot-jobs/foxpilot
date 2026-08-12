"""Command-line entry point for the current Career Agent pipeline."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = Path.home() / ".career-agent"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="career-agent",
        description="Local-first job discovery and career decision support.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Create local Career Agent configuration.",
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
        print(f"Configuration already exists: {config_path}")
        return 0

    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Career Agent initialized: {config_path}")
    print("Next: configure target_roles and locations, then run `career-agent scan`.")
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


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "init":
        return init_project(args)
    if args.command == "scan":
        return scan_project(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
