from __future__ import annotations

from techwill.extractors.warnings import WarningExtractor
from techwill.models import CommitRecord, IssueRecord, PRRecord, ReviewComment


def test_warning_extractor_scans_multiple_sources() -> None:
    commits = [
        CommitRecord(
            sha="a" * 40,
            message="temporary fix for scheduler race",
            authored_date="2026-01-01T00:00:00+00:00",
            author_name="alice",
            author_email="alice@example.com",
        )
    ]
    prs = [
        PRRecord(
            number=17,
            title="Refactor parser",
            state="open",
            merged=False,
            url="https://example/pr/17",
            unresolved_review_comments=[
                ReviewComment(
                    text="be careful when touching token cache",
                    context="PR #17: Refactor parser",
                    source_url="https://example/pr/17#comment-1",
                )
            ],
        )
    ]
    issues = [
        IssueRecord(
            number=8,
            title="Fragile migration rollback",
            state="open",
            url="https://example/issues/8",
            body="not sure about rollback ordering",
            comments=["should revisit after release"],
        )
    ]

    signals = WarningExtractor().extract(commits=commits, prs=prs, issues=issues)

    assert len(signals) >= 4
    texts = [signal.text.lower() for signal in signals]
    assert any("temporary fix" in text for text in texts)
    assert any("be careful" in text for text in texts)
    assert any("fragile migration rollback" in text for text in texts)
    assert any("not sure about rollback ordering" in text for text in texts)

