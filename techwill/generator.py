from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Protocol

from techwill.models import ContributionProfile, UnfinishedItem, WarningSignal, WillDocument


class LLMClientLike(Protocol):
    def complete(self, *, system_prompt: str, user_prompt: str) -> str: ...


class TechnicalWillGenerator:
    """Two-stage will generation: structured JSON then narrative markdown."""

    def __init__(self, llm_client: LLMClientLike) -> None:
        self.llm_client = llm_client

    def generate(self, profile: ContributionProfile, *, mode: str, strict: bool = False) -> WillDocument:
        stage1_json = self.llm_client.complete(
            system_prompt=self._stage1_system_prompt(),
            user_prompt=self._stage1_user_prompt(profile),
        )
        stage1 = self._parse_stage1(stage1_json, strict=strict)

        markdown = self.llm_client.complete(
            system_prompt=self._stage2_system_prompt(),
            user_prompt=self._stage2_user_prompt(
                profile=profile,
                mode=mode,
                stage1=stage1,
            ),
        )

        unfinished = [self._to_unfinished_item(item) for item in stage1["unfinished_summary"]]
        warnings = [self._to_warning_signal(item) for item in stage1["warning_summary"]]
        now = datetime.now(UTC).isoformat()
        will = WillDocument(
            author_handle=profile.author_handle,
            repo=profile.repo,
            generated_at=now,
            mode=mode,
            unfinished=unfinished,
            warnings=warnings,
            exclusive_knowledge=profile.exclusive_files,
            priorities=list(stage1["priorities"]),
            biggest_concern=str(stage1["biggest_concern"]),
            markdown=markdown,
        )
        if strict:
            self._validate_markdown(will.markdown)
        return will

    def generate_deterministic(self, profile: ContributionProfile, *, mode: str) -> WillDocument:
        unfinished = list(profile.unfinished_items)
        warnings = list(profile.warning_signals)
        priorities = [item.title for item in unfinished[:5]]
        if not priorities:
            priorities = ["Review high-churn modules and open issues"]
        biggest_concern = (
            warnings[0].text if warnings else "Knowledge concentration risk in exclusive modules."
        )
        now = datetime.now(UTC).isoformat()
        markdown = self._render_markdown(
            author_handle=profile.author_handle,
            repo=profile.repo,
            generated_at=now,
            mode=mode,
            unfinished=unfinished,
            warnings=warnings,
            exclusive_knowledge=profile.exclusive_files,
            priorities=priorities,
            biggest_concern=biggest_concern,
        )
        return WillDocument(
            author_handle=profile.author_handle,
            repo=profile.repo,
            generated_at=now,
            mode=mode,
            unfinished=unfinished,
            warnings=warnings,
            exclusive_knowledge=profile.exclusive_files,
            priorities=priorities,
            biggest_concern=biggest_concern,
            markdown=markdown,
        )

    def _stage1_system_prompt(self) -> str:
        return (
            "You extract structured technical intent. "
            "Return strictly valid JSON with keys: unfinished_summary, warning_summary, priorities, biggest_concern. "
            "No markdown. No extra keys."
        )

    def _stage2_system_prompt(self) -> str:
        return (
            "You write a technical will in markdown grounded only in provided data. "
            "No fabrication. Mark any inference explicitly."
        )

    def _stage1_user_prompt(self, profile: ContributionProfile) -> str:
        profile_json = json.dumps(asdict(profile), indent=2)
        return (
            "Given this ContributionProfile JSON, produce structured JSON only.\n\n"
            "Expected schema:\n"
            "{\n"
            '  "unfinished_summary": [\n'
            '    {"type":"branch|issue|todo|pr","title":"...","description":"...","evidence":"...","source_url":null}\n'
            "  ],\n"
            '  "warning_summary": [\n'
            '    {"text":"...","context":"...","source_url":null,"severity":"high|medium|low"}\n'
            "  ],\n"
            '  "priorities": ["..."],\n'
            '  "biggest_concern": "..."\n'
            "}\n\n"
            f"ContributionProfile:\n{profile_json}"
        )

    def _stage2_user_prompt(self, *, profile: ContributionProfile, mode: str, stage1: dict[str, Any]) -> str:
        structured = json.dumps(stage1, indent=2)
        return (
            f"Render the final markdown will for @{profile.author_handle} in {mode} mode.\n"
            "Use this exact section order:\n"
            "# Technical Will of @{handle}\n"
            "**Repository:** {repo}\n"
            "**Generated:** {date}\n"
            "**Mode:** {offboarding | archaeology}\n\n"
            "## What I Intended to Finish\n"
            "## What I Warned About\n"
            "## What Only I Know\n"
            "## What I'd Do Next (Priority Order)\n"
            "## What Worries Me Most\n\n"
            "Structured input:\n"
            f"{structured}\n"
        )

    def _parse_stage1(self, content: str, *, strict: bool) -> dict[str, Any]:
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Stage 1 response must be a JSON object")
        required_keys = ("unfinished_summary", "warning_summary", "priorities", "biggest_concern")
        for key in required_keys:
            if key not in parsed:
                raise ValueError(f"Stage 1 response missing key: {key}")
        if not isinstance(parsed["unfinished_summary"], list):
            raise ValueError("unfinished_summary must be a list")
        if not isinstance(parsed["warning_summary"], list):
            raise ValueError("warning_summary must be a list")
        if not isinstance(parsed["priorities"], list):
            raise ValueError("priorities must be a list")
        if not isinstance(parsed["biggest_concern"], str):
            raise ValueError("biggest_concern must be a string")
        if strict:
            self._validate_stage1_items(parsed)
        return parsed

    @staticmethod
    def _to_unfinished_item(payload: dict[str, Any]) -> UnfinishedItem:
        return UnfinishedItem(
            type=str(payload.get("type", "todo")),
            title=str(payload.get("title", "")),
            description=str(payload.get("description", "")),
            evidence=str(payload.get("evidence", "")),
            source_url=payload.get("source_url"),
            confidence=float(payload.get("confidence", 0.7)),
            evidence_kind=str(payload.get("evidence_kind", "direct")),
        )

    @staticmethod
    def _to_warning_signal(payload: dict[str, Any]) -> WarningSignal:
        return WarningSignal(
            text=str(payload.get("text", "")),
            context=str(payload.get("context", "")),
            source_url=payload.get("source_url"),
            severity=str(payload.get("severity", "medium")),
            confidence=float(payload.get("confidence", 0.7)),
            evidence_kind=str(payload.get("evidence_kind", "direct")),
        )

    @staticmethod
    def _validate_stage1_items(payload: dict[str, Any]) -> None:
        for item in payload["unfinished_summary"]:
            if not isinstance(item, dict):
                raise ValueError("Each unfinished_summary item must be an object")
            for key in ("type", "title", "description", "evidence"):
                if not isinstance(item.get(key), str):
                    raise ValueError(f"unfinished_summary item missing string key: {key}")
        for item in payload["warning_summary"]:
            if not isinstance(item, dict):
                raise ValueError("Each warning_summary item must be an object")
            if not isinstance(item.get("text"), str) or not isinstance(item.get("context"), str):
                raise ValueError("warning_summary item must include string text/context")

    @staticmethod
    def _validate_markdown(markdown: str) -> None:
        required = (
            "# Technical Will of @",
            "## What I Intended to Finish",
            "## What I Warned About",
            "## What Only I Know",
            "## What I'd Do Next (Priority Order)",
            "## What Worries Me Most",
        )
        for section in required:
            if section not in markdown:
                raise ValueError(f"Missing required markdown section: {section}")

    @staticmethod
    def _render_markdown(
        *,
        author_handle: str,
        repo: str,
        generated_at: str,
        mode: str,
        unfinished: list[UnfinishedItem],
        warnings: list[WarningSignal],
        exclusive_knowledge: list[str],
        priorities: list[str],
        biggest_concern: str,
    ) -> str:
        unfinished_lines = [
            f"- **{item.title}** — {item.description}\n  > *Evidence: {item.evidence}*"
            for item in unfinished
        ] or ["- No explicit unfinished items detected from current signals."]
        warning_lines = [
            f"- **[{w.severity.upper()}]** {w.text} — {w.context}"
            for w in warnings
        ] or ["- No warning signals detected."]
        exclusive_lines = [f"- `{p}`" for p in exclusive_knowledge] or ["- None identified"]
        priority_lines = [f"{idx}. {p}" for idx, p in enumerate(priorities, start=1)]

        return "\n".join(
            [
                f"# Technical Will of @{author_handle}",
                f"**Repository:** {repo}",
                f"**Generated:** {generated_at}",
                f"**Mode:** {mode}",
                "",
                "## What I Intended to Finish",
                *unfinished_lines,
                "",
                "## What I Warned About",
                *warning_lines,
                "",
                "## What Only I Know",
                *exclusive_lines,
                "",
                "## What I'd Do Next (Priority Order)",
                *priority_lines,
                "",
                "## What Worries Me Most",
                biggest_concern,
            ]
        )

