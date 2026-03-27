from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from techwill.models import IssueRecord, WarningSignal

WARNING_LANGUAGE = (
    "this will break",
    "be careful",
    "don't touch",
    "temporary fix",
    "fragile",
    "workaround",
    "not sure",
    "should revisit",
)


class _GithubLike(Protocol):
    def get_repo(self, full_name_or_id: str): ...


@dataclass(slots=True)
class ExtractedIssues:
    issues_opened: list[IssueRecord]
    warning_signals: list[WarningSignal]


class IssueExtractor:
    """Extract open issues by author and warning comments they left."""

    def __init__(self, github_client: _GithubLike | None = None) -> None:
        self._github_client = github_client

    def extract(self, repo: str, author_handle: str, *, max_issues: int | None = 500) -> ExtractedIssues:
        if "/" not in repo or os.path.isdir(repo):
            return ExtractedIssues(issues_opened=[], warning_signals=[])

        client = self._github_client or self._build_default_client()
        gh_repo = client.get_repo(repo)
        handle = author_handle.lower().lstrip("@")

        issues_opened: list[IssueRecord] = []
        warning_signals: list[WarningSignal] = []

        count = 0
        for issue in gh_repo.get_issues(state="open", sort="updated", direction="desc"):
            if max_issues is not None and count >= max_issues:
                break
            count += 1

            # Skip pull requests surfaced by issues API.
            if getattr(issue, "pull_request", None) is not None:
                continue

            opener = (getattr(issue.user, "login", "") or "").lower()
            if opener == handle:
                issues_opened.append(
                    IssueRecord(
                        number=issue.number,
                        title=issue.title,
                        state=issue.state,
                        url=issue.html_url,
                        body=issue.body or "",
                    )
                )

            for comment in issue.get_comments():
                comment_author = (getattr(comment.user, "login", "") or "").lower()
                body = (comment.body or "").strip()
                if comment_author != handle or not body:
                    continue
                lowered = body.lower()
                if any(keyword in lowered for keyword in WARNING_LANGUAGE):
                    warning_signals.append(
                        WarningSignal(
                            text=body,
                            context=f"Issue #{issue.number}: {issue.title}",
                            source_url=getattr(comment, "html_url", None),
                            severity="medium",
                        )
                    )

        return ExtractedIssues(issues_opened=issues_opened, warning_signals=warning_signals)

    def _build_default_client(self):
        from github import Github

        token = os.getenv("GITHUB_TOKEN")
        return Github(login_or_token=token) if token else Github()

