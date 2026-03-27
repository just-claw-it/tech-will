from __future__ import annotations

from techwill.models import CommitRecord, IssueRecord, PRRecord, WarningSignal

DEFAULT_WARNING_PATTERNS: tuple[str, ...] = (
    "this will break if",
    "temporary fix",
    "not sure about",
    "should revisit",
    "fragile",
    "be careful",
    "don't touch",
    "hack",
    "workaround",
)


class WarningExtractor:
    """Scan extracted sources for warning/risk signal language."""

    def __init__(self, warning_patterns: list[str] | None = None) -> None:
        self.warning_patterns = tuple(warning_patterns or list(DEFAULT_WARNING_PATTERNS))

    def extract(
        self,
        *,
        commits: list[CommitRecord] | None = None,
        prs: list[PRRecord] | None = None,
        issues: list[IssueRecord] | None = None,
    ) -> list[WarningSignal]:
        signals: list[WarningSignal] = []
        seen: set[tuple[str, str]] = set()

        for commit in commits or []:
            self._append_from_text(
                text=commit.message,
                context=f"Commit {commit.sha[:12]}",
                source_url=commit.html_url,
                out=signals,
                seen=seen,
            )

        for pr in prs or []:
            self._append_from_text(
                text=pr.title,
                context=f"PR #{pr.number}: {pr.title}",
                source_url=pr.url,
                out=signals,
                seen=seen,
            )
            for comment in pr.unresolved_review_comments:
                self._append_from_text(
                    text=comment.text,
                    context=comment.context,
                    source_url=comment.source_url,
                    out=signals,
                    seen=seen,
                )

        for issue in issues or []:
            self._append_from_text(
                text=issue.title,
                context=f"Issue #{issue.number}: {issue.title}",
                source_url=issue.url,
                out=signals,
                seen=seen,
            )
            if issue.body:
                self._append_from_text(
                    text=issue.body,
                    context=f"Issue #{issue.number}: {issue.title}",
                    source_url=issue.url,
                    out=signals,
                    seen=seen,
                )
            for comment_body in issue.comments:
                self._append_from_text(
                    text=comment_body,
                    context=f"Issue #{issue.number}: {issue.title}",
                    source_url=issue.url,
                    out=signals,
                    seen=seen,
                )

        return signals

    def _append_from_text(
        self,
        *,
        text: str,
        context: str,
        source_url: str | None,
        out: list[WarningSignal],
        seen: set[tuple[str, str]],
    ) -> None:
        lowered = (text or "").lower()
        for pattern in self.warning_patterns:
            if pattern in lowered:
                key = (text.strip(), context.strip())
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    WarningSignal(
                        text=text.strip(),
                        context=context,
                        source_url=source_url,
                        severity="medium",
                        confidence=0.9 if source_url else 0.75,
                        evidence_kind="direct",
                    )
                )
                break

