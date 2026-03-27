from __future__ import annotations

from dataclasses import dataclass

from techwill.extractors.prs import PRExtractor


@dataclass
class FakeUser:
    login: str


@dataclass
class FakeComment:
    body: str
    user: FakeUser
    html_url: str


@dataclass
class FakePR:
    number: int
    title: str
    state: str
    user: FakeUser
    html_url: str
    merged_at: str | None
    comments: list[FakeComment]

    def get_review_comments(self) -> list[FakeComment]:
        return self.comments


class FakeRepo:
    def __init__(self, prs: list[FakePR]) -> None:
        self._prs = prs

    def get_pulls(self, **_: object) -> list[FakePR]:
        return self._prs


class FakeGithub:
    def __init__(self, repo: FakeRepo) -> None:
        self._repo = repo

    def get_repo(self, _: str) -> FakeRepo:
        return self._repo


def test_pr_extractor_collects_authored_prs_and_risk_comments() -> None:
    prs = [
        FakePR(
            number=11,
            title="Auth refactor",
            state="open",
            user=FakeUser("alice"),
            html_url="https://example/pr/11",
            merged_at=None,
            comments=[
                FakeComment(
                    body="be careful with this edge case",
                    user=FakeUser("alice"),
                    html_url="https://example/pr/11#comment-1",
                ),
                FakeComment(
                    body="please resolve this",
                    user=FakeUser("reviewer1"),
                    html_url="https://example/pr/11#comment-2",
                ),
            ],
        ),
        FakePR(
            number=12,
            title="Docs",
            state="closed",
            user=FakeUser("bob"),
            html_url="https://example/pr/12",
            merged_at=None,
            comments=[],
        ),
    ]
    extractor = PRExtractor(github_client=FakeGithub(FakeRepo(prs)))

    result = extractor.extract("owner/repo", "alice")

    assert len(result.prs_authored) == 1
    assert result.prs_authored[0].number == 11
    assert len(result.prs_authored[0].unresolved_review_comments) == 1
    assert len(result.review_comments_by_author) == 1
    assert "be careful" in result.review_comments_by_author[0].text.lower()

