from __future__ import annotations

from techwill.analyzers.unfinished import UnfinishedAnalyzer
from techwill.models import (
    BranchRecord,
    ContributionProfile,
    IssueRecord,
    PRRecord,
    ReviewComment,
    TodoComment,
)


def test_unfinished_analyzer_collects_branch_issue_pr_todo() -> None:
    profile = ContributionProfile(author_handle="alice", repo="owner/repo")
    profile.abandoned_branches = [
        BranchRecord(
            name="feature/alice-wip",
            last_commit_sha="a" * 40,
            last_commit_message="wip workaround",
            last_commit_date="2026-01-01T00:00:00+00:00",
        )
    ]
    profile.issues_opened = [IssueRecord(number=1, title="Open issue", state="open", url="https://example/i/1")]
    profile.prs_authored = [
        PRRecord(
            number=2,
            title="Unmerged PR",
            state="open",
            merged=False,
            url="https://example/p/2",
            unresolved_review_comments=[ReviewComment(text="needs follow-up", context="PR #2: Unmerged PR")],
        )
    ]
    profile.todo_comments = [TodoComment(commit_sha="b" * 40, file_path="src/a.py", text="TODO: final step")]

    items = UnfinishedAnalyzer().analyze(profile)

    assert {item.type for item in items} == {"branch", "issue", "pr", "todo"}

