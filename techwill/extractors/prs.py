from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from techwill.models import PRRecord, ReviewComment

RISK_LANGUAGE = (
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
class ExtractedPRs:
    prs_authored: list[PRRecord]
    review_comments_by_author: list[ReviewComment]


class PRExtractor:
    """Extract PR records and review comments for an author."""

    def __init__(self, github_client: _GithubLike | None = None) -> None:
        self._github_client = github_client

    def extract(self, repo: str, author_handle: str, *, max_prs: int | None = 200) -> ExtractedPRs:
        if "/" not in repo or os.path.isdir(repo):
            return ExtractedPRs(prs_authored=[], review_comments_by_author=[])

        client = self._github_client or self._build_default_client()
        gh_repo = client.get_repo(repo)
        handle = author_handle.lower().lstrip("@")

        prs_authored: list[PRRecord] = []
        review_comments_by_author: list[ReviewComment] = []

        count = 0
        for pr in gh_repo.get_pulls(state="all", sort="updated", direction="desc"):
            if max_prs is not None and count >= max_prs:
                break
            count += 1

            pr_author = (getattr(pr.user, "login", "") or "").lower()
            pr_comments = list(pr.get_review_comments())

            if pr_author == handle:
                unresolved = [
                    ReviewComment(
                        text=(comment.body or "").strip(),
                        context=f"PR #{pr.number}: {pr.title}",
                        source_url=getattr(comment, "html_url", None),
                    )
                    for comment in pr_comments
                    if (comment.body or "").strip() and (getattr(comment.user, "login", "") or "").lower() != handle
                ]
                prs_authored.append(
                    PRRecord(
                        number=pr.number,
                        title=pr.title,
                        state=pr.state,
                        merged=bool(pr.merged_at),
                        url=pr.html_url,
                        unresolved_review_comments=unresolved,
                    )
                )

            for comment in pr_comments:
                comment_author = (getattr(comment.user, "login", "") or "").lower()
                body = (comment.body or "").strip()
                if comment_author != handle or not body:
                    continue
                if any(kw in body.lower() for kw in RISK_LANGUAGE):
                    review_comments_by_author.append(
                        ReviewComment(
                            text=body,
                            context=f"PR #{pr.number}: {pr.title}",
                            source_url=getattr(comment, "html_url", None),
                        )
                    )

        return ExtractedPRs(
            prs_authored=prs_authored,
            review_comments_by_author=review_comments_by_author,
        )

    def _build_default_client(self):
        from github import Github

        token = os.getenv("GITHUB_TOKEN")
        return Github(login_or_token=token) if token else Github()

