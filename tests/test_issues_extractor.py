from __future__ import annotations

from dataclasses import dataclass

from techwill.extractors.issues import IssueExtractor


@dataclass
class FakeUser:
    login: str


@dataclass
class FakeComment:
    body: str
    user: FakeUser
    html_url: str


@dataclass
class FakeIssue:
    number: int
    title: str
    state: str
    body: str
    user: FakeUser
    html_url: str
    comments: list[FakeComment]
    pull_request: object | None = None

    def get_comments(self) -> list[FakeComment]:
        return self.comments


class FakeRepo:
    def __init__(self, issues: list[FakeIssue]) -> None:
        self._issues = issues

    def get_issues(self, **_: object) -> list[FakeIssue]:
        return self._issues


class FakeGithub:
    def __init__(self, repo: FakeRepo) -> None:
        self._repo = repo

    def get_repo(self, _: str) -> FakeRepo:
        return self._repo


def test_issue_extractor_collects_opened_and_warning_signals() -> None:
    issues = [
        FakeIssue(
            number=21,
            title="Broken migrations",
            state="open",
            body="Need to revisit migration runner",
            user=FakeUser("alice"),
            html_url="https://example/issues/21",
            comments=[
                FakeComment(
                    body="this will break in production if retried",
                    user=FakeUser("alice"),
                    html_url="https://example/issues/21#comment-1",
                ),
                FakeComment(
                    body="please add tests",
                    user=FakeUser("reviewer"),
                    html_url="https://example/issues/21#comment-2",
                ),
            ],
        ),
        FakeIssue(
            number=22,
            title="Ignore PR item",
            state="open",
            body="",
            user=FakeUser("alice"),
            html_url="https://example/issues/22",
            comments=[],
            pull_request=object(),
        ),
    ]
    extractor = IssueExtractor(github_client=FakeGithub(FakeRepo(issues)))

    result = extractor.extract("owner/repo", "@alice")

    assert len(result.issues_opened) == 1
    assert result.issues_opened[0].number == 21
    assert len(result.warning_signals) == 1
    assert "will break" in result.warning_signals[0].text.lower()

