from __future__ import annotations

from techwill.analyzers.knowledge_map import KnowledgeMapAnalyzer
from techwill.models import CommitRecord


def _commit(
    *,
    sha: str,
    author_name: str,
    author_email: str,
    files_touched: list[str],
) -> CommitRecord:
    return CommitRecord(
        sha=sha,
        message="commit",
        authored_date="2026-01-01T00:00:00+00:00",
        author_name=author_name,
        author_email=author_email,
        files_touched=files_touched,
    )


def test_knowledge_map_detects_exclusive_files() -> None:
    commits = [
        _commit(
            sha="1" * 40,
            author_name="Alice Example",
            author_email="alice@example.com",
            files_touched=["src/payments/core.py"],
        ),
        _commit(
            sha="2" * 40,
            author_name="Alice Example",
            author_email="alice@example.com",
            files_touched=["src/payments/core.py"],
        ),
        _commit(
            sha="3" * 40,
            author_name="Bob Example",
            author_email="bob@example.com",
            files_touched=["src/payments/core.py"],
        ),
        _commit(
            sha="4" * 40,
            author_name="Alice Example",
            author_email="alice@example.com",
            files_touched=["src/auth/flow.py"],
        ),
    ]

    analyzer = KnowledgeMapAnalyzer(dominance_threshold=0.60, max_other_contributors=1)
    exclusive = analyzer.analyze(all_commits=commits, author_handle="alice")

    assert "src/payments/core.py" in exclusive
    assert "src/auth/flow.py" in exclusive

