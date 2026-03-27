from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from techwill import cli
from techwill.config import ExtractionConfig, OutputConfig, TechWillConfig
from techwill.models import (
    BranchRecord,
    CommitRecord,
    ContributionProfile,
    IssueRecord,
    PRRecord,
    ReviewComment,
    TodoComment,
    WarningSignal,
    WillDocument,
)

runner = CliRunner()


class _DummyExtractedCommits:
    def __init__(self) -> None:
        self.commits = [
            CommitRecord(
                sha="a" * 40,
                message="temporary fix",
                authored_date="2026-01-01T00:00:00+00:00",
                author_name="alice",
                author_email="alice@example.com",
                files_touched=["src/a.py"],
                todo_fixme_additions=[TodoComment(commit_sha="a" * 40, file_path="src/a.py", text="TODO: fix")],
            )
        ]


class _DummyPRExtracted:
    def __init__(self) -> None:
        self.prs_authored = [PRRecord(number=1, title="PR", state="open", merged=False, url="https://example/pr/1")]
        self.review_comments_by_author = [
            ReviewComment(text="be careful", context="PR #1: PR", source_url="https://example/pr/1#c1")
        ]


class _DummyIssueExtracted:
    def __init__(self) -> None:
        self.issues_opened = [IssueRecord(number=1, title="Issue", state="open", url="https://example/i/1")]
        self.warning_signals = [WarningSignal(text="fragile", context="Issue #1: Issue", severity="medium")]


class _DummyBranchExtracted:
    def __init__(self) -> None:
        self.abandoned_branches = [
            BranchRecord(
                name="feature/a",
                last_commit_sha="b" * 40,
                last_commit_message="wip",
                last_commit_date="2026-01-01T00:00:00+00:00",
            )
        ]


class _DummyGenerator:
    def __init__(self, _: object) -> None:
        pass

    def generate(self, profile: ContributionProfile, *, mode: str, strict: bool = False) -> WillDocument:
        return WillDocument(
            author_handle=profile.author_handle,
            repo=profile.repo,
            generated_at="2026-03-27T00:00:00+00:00",
            mode=mode,
            markdown="# Technical Will of @alice\n",
        )


def _patch_pipeline(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    monkeypatch.setattr(cli.CommitExtractor, "extract", lambda self, *a, **k: _DummyExtractedCommits())
    monkeypatch.setattr(cli.PRExtractor, "extract", lambda self, *a, **k: _DummyPRExtracted())
    monkeypatch.setattr(cli.IssueExtractor, "extract", lambda self, *a, **k: _DummyIssueExtracted())
    monkeypatch.setattr(cli.BranchExtractor, "extract", lambda self, *a, **k: _DummyBranchExtracted())
    monkeypatch.setattr(cli.WarningSeverityAnalyzer, "classify", lambda self, warnings: warnings)
    monkeypatch.setattr(cli.TechnicalWillGenerator, "__init__", _DummyGenerator.__init__)
    monkeypatch.setattr(cli.TechnicalWillGenerator, "generate", _DummyGenerator.generate)


def test_generate_archaeology_writes_markdown_and_json(monkeypatch, tmp_path: Path) -> None:
    _patch_pipeline(monkeypatch)

    output = tmp_path / "will.md"
    result = runner.invoke(
        cli.app,
        [
            "generate",
            "--repo",
            "owner/repo",
            "--author",
            "alice",
            "--mode",
            "archaeology",
            "--format",
            "both",
            "--output",
            str(output),
            "--no-use-cache",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()
    assert output.with_suffix(".json").exists()
    payload = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    assert "metadata" in payload
    assert "signal_counts" in payload["metadata"]


def test_generate_offboarding_save_keeps_draft(monkeypatch, tmp_path: Path) -> None:
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(cli.typer, "prompt", lambda *a, **k: "s")

    output = tmp_path / "offboarding.md"
    result = runner.invoke(
        cli.app,
        [
            "generate",
            "--repo",
            "owner/repo",
            "--author",
            "alice",
            "--mode",
            "offboarding",
            "--format",
            "both",
            "--output",
            str(output),
            "--no-use-cache",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()
    assert output.with_suffix(".json").exists()


def test_generate_offboarding_discard_removes_outputs(monkeypatch, tmp_path: Path) -> None:
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(cli.typer, "prompt", lambda *a, **k: "x")

    output = tmp_path / "discard.md"
    result = runner.invoke(
        cli.app,
        [
            "generate",
            "--repo",
            "owner/repo",
            "--author",
            "alice",
            "--mode",
            "offboarding",
            "--format",
            "both",
            "--output",
            str(output),
            "--no-use-cache",
        ],
    )

    assert result.exit_code == 0
    assert not output.exists()
    assert not output.with_suffix(".json").exists()


def test_generate_uses_config_defaults_when_flags_omitted(monkeypatch, tmp_path: Path) -> None:
    _patch_pipeline(monkeypatch)

    config = TechWillConfig(
        output=OutputConfig(dir=str(tmp_path / "wills"), format="both"),
        extraction=ExtractionConfig(max_commits=77, warning_keywords=[]),
    )
    monkeypatch.setattr(cli, "load_config", lambda _: config)

    observed: dict[str, object] = {}

    def _extract_with_observe(self, repo, author, *, max_commits=None):
        observed["max_commits"] = max_commits
        return _DummyExtractedCommits()

    monkeypatch.setattr(cli.CommitExtractor, "extract", _extract_with_observe)

    result = runner.invoke(
        cli.app,
        [
            "generate",
            "--repo",
            "owner/repo",
            "--author",
            "alice",
            "--mode",
            "archaeology",
            "--no-use-cache",
        ],
    )

    expected_output = tmp_path / "wills" / "will-alice-owner-repo.md"
    assert result.exit_code == 0
    assert observed["max_commits"] == 77
    assert expected_output.exists()
    assert expected_output.with_suffix(".json").exists()


def test_generate_no_llm_uses_deterministic_path(monkeypatch, tmp_path: Path) -> None:
    _patch_pipeline(monkeypatch)
    output = tmp_path / "deterministic.md"
    result = runner.invoke(
        cli.app,
        [
            "generate",
            "--repo",
            "owner/repo",
            "--author",
            "alice",
            "--mode",
            "archaeology",
            "--no-llm",
            "--format",
            "both",
            "--output",
            str(output),
            "--no-use-cache",
        ],
    )
    assert result.exit_code == 0
    assert output.exists()
    assert "Technical Will of @alice" in output.read_text(encoding="utf-8")


def test_generate_dry_run_writes_nothing(monkeypatch, tmp_path: Path) -> None:
    _patch_pipeline(monkeypatch)
    output = tmp_path / "dryrun.md"
    result = runner.invoke(
        cli.app,
        [
            "generate",
            "--repo",
            "owner/repo",
            "--author",
            "alice",
            "--dry-run",
            "--output",
            str(output),
            "--no-use-cache",
        ],
    )
    assert result.exit_code == 0
    assert not output.exists()


def test_inspect_prints_signal_summary(monkeypatch) -> None:
    _patch_pipeline(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "inspect",
            "--repo",
            "owner/repo",
            "--author",
            "alice",
            "--no-use-cache",
        ],
    )
    assert result.exit_code == 0
    assert "Signal summary" in result.stdout


def test_validate_passes_when_required_env_present(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")

    result = runner.invoke(cli.app, ["validate"])
    assert result.exit_code == 0
    assert "[PASS] config.load:" in result.stdout
    assert "[PASS] env.llm:" in result.stdout
    assert "[PASS] env.github:" in result.stdout


def test_validate_fails_when_check_llm_requested_without_env(monkeypatch) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    result = runner.invoke(cli.app, ["validate", "--check-llm"])
    assert result.exit_code == 1
    assert "[FAIL] env.llm:" in result.stdout
    assert "[FAIL] llm.api:" in result.stdout

