from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import typer
from git import Repo
from github import Github

from techwill.analyzers.bus_factor import BusFactorAnalyzer
from techwill.analyzers.knowledge_map import KnowledgeMapAnalyzer
from techwill.analyzers.unfinished import UnfinishedAnalyzer
from techwill.analyzers.warning_severity import WarningSeverityAnalyzer
from techwill.cache import ProfileCache
from techwill.config import load_config
from techwill.extractors.branches import BranchExtractor
from techwill.extractors.commits import CommitExtractor
from techwill.extractors.issues import IssueExtractor
from techwill.extractors.prs import PRExtractor
from techwill.extractors.todos import TodoExtractor
from techwill.extractors.warnings import WarningExtractor
from techwill.generator import TechnicalWillGenerator
from techwill.llm import LLMConfig, OpenAICompatibleClient
from techwill.models import ContributionProfile

app = typer.Typer(help="Generate a technical will from contribution history.", no_args_is_help=True)


@app.command()
def generate(
    repo: str = typer.Option(..., help="GitHub repo (owner/repo) or local path."),
    author: str = typer.Option(..., help="Author handle/login/email hint."),
    mode: Literal["archaeology", "offboarding"] = typer.Option("archaeology"),
    output: Path | None = typer.Option(None, help="Output markdown path."),
    format: Literal["markdown", "json", "both"] | None = typer.Option(None),
    max_commits: int | None = typer.Option(None, help="Maximum commits to scan."),
    config: Path | None = typer.Option(None, help="Path to techwill.yaml config file."),
    no_llm: bool = typer.Option(False, help="Skip LLM and use deterministic generation."),
    strict: bool = typer.Option(False, help="Enable strict schema/markdown validation."),
    dry_run: bool = typer.Option(False, help="Run extraction and checks only; do not write outputs."),
    use_cache: bool = typer.Option(True, help="Reuse cached extraction profile when available."),
) -> None:
    """Generate technical will document."""
    cfg = load_config(config)
    resolved_format = _resolve_output_format(format or cfg.output.format)
    resolved_max_commits = max_commits if max_commits is not None else cfg.extraction.max_commits
    resolved_output = output or Path(cfg.output.dir) / f"will-{author.lstrip('@')}-{_safe_repo_slug(repo)}.md"
    profile = _build_profile(
        repo=repo,
        author=author,
        max_commits=resolved_max_commits,
        use_cache=use_cache,
    )

    severity_classified = False
    if not no_llm:
        llm_client = OpenAICompatibleClient(LLMConfig.from_env())
        warnings_before = [w.severity for w in profile.warning_signals]
        profile.warning_signals = WarningSeverityAnalyzer(llm_client).classify(profile.warning_signals)
        if [w.severity for w in profile.warning_signals] != warnings_before:
            severity_classified = True
        will = TechnicalWillGenerator(llm_client).generate(profile, mode=mode, strict=strict)
    else:
        will = TechnicalWillGenerator(_NullLLM()).generate_deterministic(profile, mode=mode)

    if dry_run:
        typer.echo("Dry run complete. No output files written.")
        typer.echo(f"Would write to: {resolved_output}")
        return

    metadata = _build_output_metadata(
        profile=profile,
        mode=mode,
        severity_classified=severity_classified,
        llm_enabled=not no_llm,
    )
    markdown_path, json_path = _persist_output(
        will,
        output=resolved_output,
        output_format=resolved_format,
        metadata=metadata,
        strict=strict,
    )
    if mode == "offboarding":
        _run_offboarding_gate(markdown_path=markdown_path, json_path=json_path)

    if markdown_path:
        typer.echo(f"Markdown saved to: {markdown_path}")
    if json_path:
        typer.echo(f"JSON saved to: {json_path}")


@app.command()
def inspect(
    repo: str = typer.Option(..., help="GitHub repo (owner/repo) or local path."),
    author: str = typer.Option(..., help="Author handle/login/email hint."),
    max_commits: int = typer.Option(500, help="Maximum commits to scan."),
    use_cache: bool = typer.Option(True, help="Reuse cached extraction profile when available."),
) -> None:
    """Inspect extracted signals without generation."""
    profile = _build_profile(repo=repo, author=author, max_commits=max_commits, use_cache=use_cache)
    typer.echo("Signal summary")
    typer.echo(f"- commits: {len(profile.commits)}")
    typer.echo(f"- prs_authored: {len(profile.prs_authored)}")
    typer.echo(f"- issues_opened: {len(profile.issues_opened)}")
    typer.echo(f"- todo_comments: {len(profile.todo_comments)}")
    typer.echo(f"- abandoned_branches: {len(profile.abandoned_branches)}")
    typer.echo(f"- warning_signals: {len(profile.warning_signals)}")
    typer.echo(f"- unfinished_items: {len(profile.unfinished_items)}")
    if profile.unfinished_items:
        typer.echo("\nTop unfinished items:")
        for item in profile.unfinished_items[:5]:
            typer.echo(f"- [{item.type}] {item.title}")


@dataclass(slots=True)
class _ValidationResult:
    check: str
    ok: bool
    detail: str


@app.command()
def validate(
    repo: str | None = typer.Option(None, help="Optional repo path or owner/repo for connectivity checks."),
    config: Path | None = typer.Option(None, help="Path to techwill.yaml config file."),
    check_remote: bool = typer.Option(False, help="Verify GitHub API access when repo is owner/repo."),
    check_llm: bool = typer.Option(False, help="Verify LLM endpoint credentials and reachability."),
) -> None:
    """Validate environment, config, and optional service connectivity."""
    results: list[_ValidationResult] = []
    cfg = load_config(config)
    results.append(_ValidationResult("config.load", True, f"Loaded config (output.dir={cfg.output.dir})"))

    llm_env_present = all(
        bool(os.getenv(name, "").strip()) for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
    )
    results.append(
        _ValidationResult(
            "env.llm",
            llm_env_present,
            "LLM env vars present" if llm_env_present else "Missing one or more of LLM_BASE_URL, LLM_API_KEY, LLM_MODEL",
        )
    )

    gh_token_present = bool(os.getenv("GITHUB_TOKEN", "").strip())
    results.append(
        _ValidationResult(
            "env.github",
            gh_token_present,
            "GITHUB_TOKEN present" if gh_token_present else "GITHUB_TOKEN not set (public-only access/rate limits apply)",
        )
    )

    if repo:
        if Path(repo).exists():
            try:
                Repo(repo)
                results.append(_ValidationResult("repo.local", True, f"Local repo readable: {repo}"))
            except Exception as exc:
                results.append(_ValidationResult("repo.local", False, f"Failed to open local repo: {exc}"))
        else:
            results.append(_ValidationResult("repo.local", False, f"Path does not exist: {repo}"))

        if check_remote and "/" in repo and not Path(repo).exists():
            try:
                gh = Github(login_or_token=os.getenv("GITHUB_TOKEN", "")) if gh_token_present else Github()
                gh.get_repo(repo).full_name
                results.append(_ValidationResult("github.api", True, f"GitHub repo reachable: {repo}"))
            except Exception as exc:
                results.append(_ValidationResult("github.api", False, f"GitHub lookup failed: {exc}"))

    if check_llm:
        if not llm_env_present:
            results.append(_ValidationResult("llm.api", False, "Skipped (missing LLM env vars)"))
        else:
            try:
                client = OpenAICompatibleClient(LLMConfig.from_env())
                _ = client.complete(system_prompt="Respond with OK", user_prompt="OK")
                results.append(_ValidationResult("llm.api", True, "LLM API reachable"))
            except Exception as exc:
                results.append(_ValidationResult("llm.api", False, f"LLM check failed: {exc}"))

    failed = False
    for result in results:
        prefix = "PASS" if result.ok else "FAIL"
        typer.echo(f"[{prefix}] {result.check}: {result.detail}")
        if not result.ok:
            failed = True

    if failed:
        raise typer.Exit(code=1)


def _persist_output(
    will_document,
    *,
    output: Path | None,
    output_format: Literal["markdown", "json", "both"],
    metadata: dict[str, Any] | None = None,
    strict: bool = False,
) -> tuple[Path | None, Path | None]:
    out_md = output or Path(f"will-{will_document.author_handle}-{_safe_repo_slug(will_document.repo)}.md")
    out_json = out_md.with_suffix(".json")

    markdown_path: Path | None = None
    json_path: Path | None = None

    if output_format in {"markdown", "both"}:
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(will_document.markdown, encoding="utf-8")
        markdown_path = out_md

    if output_format in {"json", "both"}:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(will_document)
        payload["metadata"] = metadata or {}
        if strict:
            _validate_output_payload(payload)
        out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        json_path = out_json

    return markdown_path, json_path


def _safe_repo_slug(repo: str) -> str:
    slug = repo.replace("https://github.com/", "").replace(".git", "")
    return slug.replace("/", "-").replace("\\", "-").replace(" ", "-")


def _resolve_output_format(value: str) -> Literal["markdown", "json", "both"]:
    normalized = value.strip().lower()
    if normalized not in {"markdown", "json", "both"}:
        raise typer.BadParameter("format must be one of: markdown, json, both")
    return cast(Literal["markdown", "json", "both"], normalized)


def _build_output_metadata(
    *,
    profile: ContributionProfile,
    mode: str,
    severity_classified: bool,
    llm_enabled: bool,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "signal_counts": {
            "commits": len(profile.commits),
            "prs_authored": len(profile.prs_authored),
            "issues_opened": len(profile.issues_opened),
            "todo_comments": len(profile.todo_comments),
            "abandoned_branches": len(profile.abandoned_branches),
            "warning_signals": len(profile.warning_signals),
            "unfinished_items": len(profile.unfinished_items),
            "exclusive_files": len(profile.exclusive_files),
            "bus_factor_modules": len(profile.bus_factor_modules),
        },
        "quality": {
            "confidence_note": (
                "Generated from available commits/PRs/issues/branches. "
                "Completeness may be reduced for deleted/private artifacts."
            ),
            "inference_policy": "Narrative inferences should be explicitly marked in markdown output.",
        },
        "flags": {
            "contains_llm_inference": llm_enabled,
            "warning_severity_llm_classified": severity_classified,
        },
    }


def _build_profile(
    *,
    repo: str,
    author: str,
    max_commits: int,
    use_cache: bool,
) -> ContributionProfile:
    cache = ProfileCache()
    if use_cache:
        cached = cache.load(repo=repo, author=author, max_commits=max_commits)
        if cached:
            return cached

    commit_result = CommitExtractor().extract(repo, author, max_commits=max_commits)
    todo_comments = TodoExtractor().extract_from_commits(commit_result.commits)
    pr_result = PRExtractor().extract(repo, author)
    issue_result = IssueExtractor().extract(repo, author)
    branch_result = BranchExtractor().extract(repo, author)

    warnings = WarningExtractor().extract(
        commits=commit_result.commits,
        prs=pr_result.prs_authored,
        issues=issue_result.issues_opened,
    )
    warnings.extend(issue_result.warning_signals)

    profile = ContributionProfile(
        author_handle=author.lstrip("@"),
        repo=repo,
        commits=commit_result.commits,
        prs_authored=pr_result.prs_authored,
        issues_opened=issue_result.issues_opened,
        review_comments=pr_result.review_comments_by_author,
        todo_comments=todo_comments,
        abandoned_branches=branch_result.abandoned_branches,
        warning_signals=warnings,
    )
    profile.unfinished_items = UnfinishedAnalyzer().analyze(profile)
    exclusive_files = KnowledgeMapAnalyzer().analyze(all_commits=profile.commits, author_handle=author)
    profile.exclusive_files = exclusive_files
    profile.bus_factor_modules = BusFactorAnalyzer().analyze(exclusive_files=exclusive_files)
    if use_cache:
        cache.save(profile, max_commits=max_commits)
    return profile


class _NullLLM:
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("Null LLM should not be called")


def _validate_output_payload(payload: dict[str, Any]) -> None:
    required = {"author_handle", "repo", "generated_at", "mode", "unfinished", "warnings", "markdown", "metadata"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"Output JSON missing keys: {sorted(missing)}")
    if not isinstance(payload["unfinished"], list) or not isinstance(payload["warnings"], list):
        raise ValueError("Output JSON unfinished/warnings must be lists")
    if not isinstance(payload["metadata"], dict):
        raise ValueError("Output JSON metadata must be an object")


def _run_offboarding_gate(*, markdown_path: Path | None, json_path: Path | None) -> None:
    if not markdown_path:
        raise typer.BadParameter("Offboarding mode requires markdown output (--format markdown|both).")

    typer.echo("══════════════════════════════════════")
    typer.echo("OFFBOARDING MODE — Review Before Sharing")
    typer.echo("══════════════════════════════════════")
    typer.echo(f"The technical will has been generated.\nReview it at: {markdown_path}")
    typer.echo("")
    typer.echo("Actions:")
    typer.echo("  (a) approve and share with team")
    typer.echo("  (e) open in editor to annotate")
    typer.echo("  (s) save draft only, share later")
    typer.echo("  (x) discard")
    choice = typer.prompt("Your choice", default="s").strip().lower()

    if choice == "a":
        typer.echo("Approved. Share this document with your team when ready.")
        return
    if choice == "e":
        _open_in_editor(markdown_path)
        typer.echo("Opened in editor. Draft remains saved.")
        return
    if choice == "s":
        typer.echo("Draft saved.")
        return
    if choice == "x":
        markdown_path.unlink(missing_ok=True)
        if json_path:
            json_path.unlink(missing_ok=True)
        raise typer.Exit(code=0)

    typer.echo("Unrecognized choice. Keeping draft saved.")


def _open_in_editor(path: Path) -> None:
    editor = os.getenv("EDITOR")
    if editor:
        subprocess.run([editor, str(path)], check=False)
        return
    # Fallback for macOS; no-op errors are acceptable.
    subprocess.run(["open", str(path)], check=False)


@app.command()
def contributors(
    repo: str = typer.Option(..., help="Local repo path (v1) or owner/repo (coming next)."),
    min_commits: int = typer.Option(10, help="Minimum commit count threshold."),
) -> None:
    """List contributors and commit counts (local repo support in v1)."""
    if not Path(repo).exists():
        raise typer.BadParameter("Contributors command currently supports local repo paths in this build.")

    git_repo = Repo(repo)
    counts: dict[str, int] = {}
    for commit in git_repo.iter_commits("--all"):
        identity = (commit.author.name or commit.author.email or "unknown").strip()
        counts[identity] = counts.get(identity, 0) + 1

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    for identity, count in ranked:
        if count >= min_commits:
            typer.echo(f"{identity}: {count}")


if __name__ == "__main__":
    app()

