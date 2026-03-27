from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


def build_command(
    *,
    repo: str,
    author: str,
    mode: str = "archaeology",
    output: str | None = None,
    format: str = "markdown",
    max_commits: int = 1000,
) -> list[str]:
    cmd = [
        "tech-will",
        "generate",
        "--repo",
        repo,
        "--author",
        author.lstrip("@"),
        "--mode",
        mode,
        "--format",
        format,
        "--max-commits",
        str(max_commits),
    ]
    if output:
        cmd.extend(["--output", output])
    return cmd


def run_command(cmd: list[str]) -> int:
    print(f"Running: {shlex.join(cmd)}")
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run tech-will CLI for OpenClaw skill integration.")
    parser.add_argument("--repo", required=True, help="owner/repo or local path")
    parser.add_argument("--author", required=True, help="author handle/login")
    parser.add_argument("--mode", choices=["archaeology", "offboarding"], default="archaeology")
    parser.add_argument("--output", default=None, help="markdown output path")
    parser.add_argument("--format", choices=["markdown", "json", "both"], default="markdown")
    parser.add_argument("--max-commits", type=int, default=1000)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    output = str(Path(args.output).expanduser()) if args.output else None
    cmd = build_command(
        repo=args.repo,
        author=args.author,
        mode=args.mode,
        output=output,
        format=args.format,
        max_commits=args.max_commits,
    )
    return run_command(cmd)


if __name__ == "__main__":
    raise SystemExit(main())

