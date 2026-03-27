from __future__ import annotations

import json

from techwill.generator import TechnicalWillGenerator
from techwill.models import ContributionProfile


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        if len(self.calls) == 1:
            return json.dumps(
                {
                    "unfinished_summary": [
                        {
                            "type": "todo",
                            "title": "Finalize parser cleanup",
                            "description": "Edge-case parser paths remain.",
                            "evidence": "TODO: tighten parser",
                            "source_url": None,
                        }
                    ],
                    "warning_summary": [
                        {
                            "text": "temporary fix around retry loop",
                            "context": "Commit abc",
                            "source_url": None,
                            "severity": "high",
                        }
                    ],
                    "priorities": ["Close parser TODOs", "Resolve retry edge-case"],
                    "biggest_concern": "Retry loop can duplicate side effects under high latency.",
                }
            )
        return (
            "# Technical Will of @alice\n"
            "**Repository:** owner/repo\n"
            "**Generated:** 2026-03-27T00:00:00Z\n"
            "**Mode:** archaeology\n\n"
            "## What I Intended to Finish\n"
            "- parser cleanup\n"
        )


class FakeBadMarkdownLLM:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        if self.calls == 1:
            return json.dumps(
                {
                    "unfinished_summary": [],
                    "warning_summary": [],
                    "priorities": ["One"],
                    "biggest_concern": "None",
                }
            )
        return "not a structured markdown output"


def test_generator_runs_two_stage_pipeline_and_builds_document() -> None:
    profile = ContributionProfile(author_handle="alice", repo="owner/repo")
    profile.exclusive_files = ["src/parser/core.py"]

    llm = FakeLLM()
    generator = TechnicalWillGenerator(llm)
    will = generator.generate(profile, mode="archaeology")

    assert len(llm.calls) == 2
    assert will.author_handle == "alice"
    assert will.repo == "owner/repo"
    assert will.mode == "archaeology"
    assert will.unfinished[0].title == "Finalize parser cleanup"
    assert will.warnings[0].severity == "high"
    assert will.exclusive_knowledge == ["src/parser/core.py"]
    assert will.priorities == ["Close parser TODOs", "Resolve retry edge-case"]
    assert "Technical Will of @alice" in will.markdown


def test_generator_deterministic_mode_renders_sections() -> None:
    profile = ContributionProfile(author_handle="alice", repo="owner/repo")
    profile.exclusive_files = ["src/parser/core.py"]
    llm = FakeLLM()
    generator = TechnicalWillGenerator(llm)
    will = generator.generate_deterministic(profile, mode="archaeology")
    assert "## What I Intended to Finish" in will.markdown
    assert will.mode == "archaeology"


def test_generator_strict_mode_validates_markdown_sections() -> None:
    profile = ContributionProfile(author_handle="alice", repo="owner/repo")
    generator = TechnicalWillGenerator(FakeBadMarkdownLLM())
    try:
        generator.generate(profile, mode="archaeology", strict=True)
    except ValueError as exc:
        assert "Missing required markdown section" in str(exc)
        return
    raise AssertionError("Expected strict validation error")

