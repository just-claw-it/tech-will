from __future__ import annotations

from techwill.models import ContributionProfile, UnfinishedItem


class UnfinishedAnalyzer:
    """Derive unfinished intent signals from extracted contribution data."""

    def analyze(self, profile: ContributionProfile) -> list[UnfinishedItem]:
        items: list[UnfinishedItem] = []

        for branch in profile.abandoned_branches:
            items.append(
                UnfinishedItem(
                    type="branch",
                    title=branch.name,
                    description="Branch appears unmerged and likely abandoned.",
                    evidence=branch.last_commit_message,
                    source_url=branch.source_url,
                    confidence=0.8 if branch.source_url else 0.72,
                    evidence_kind="direct",
                )
            )

        for issue in profile.issues_opened:
            if issue.state.lower() == "open":
                evidence = (issue.body or "").strip() or issue.title
                items.append(
                    UnfinishedItem(
                        type="issue",
                        title=issue.title,
                        description="Issue opened by author is still open.",
                        evidence=evidence,
                        source_url=issue.url,
                        confidence=0.9,
                        evidence_kind="direct",
                    )
                )

        for pr in profile.prs_authored:
            if not pr.merged:
                evidence = pr.title
                if pr.unresolved_review_comments:
                    evidence = pr.unresolved_review_comments[0].text
                items.append(
                    UnfinishedItem(
                        type="pr",
                        title=pr.title,
                        description="PR appears unmerged or has unresolved review feedback.",
                        evidence=evidence,
                        source_url=pr.url,
                        confidence=0.9,
                        evidence_kind="direct",
                    )
                )

        for todo in profile.todo_comments:
            items.append(
                UnfinishedItem(
                    type="todo",
                    title=f"{todo.file_path}: TODO/FIXME",
                    description="TODO/FIXME marker added in author commit.",
                    evidence=todo.text,
                    source_url=None,
                    confidence=0.85,
                    evidence_kind="direct",
                )
            )

        return items

