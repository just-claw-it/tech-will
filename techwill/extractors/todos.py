from __future__ import annotations

from techwill.extractors.commits import CommitExtractor
from techwill.models import CommitRecord, TodoComment


class TodoExtractor:
    """Extract TODO/FIXME comments from an author's commits."""

    def extract_from_commits(self, commits: list[CommitRecord]) -> list[TodoComment]:
        todos: list[TodoComment] = []
        for commit in commits:
            todos.extend(commit.todo_fixme_additions)
        return todos

    def extract(
        self,
        repo: str,
        author_handle: str,
        *,
        max_commits: int | None = None,
        commit_extractor: CommitExtractor | None = None,
    ) -> list[TodoComment]:
        extractor = commit_extractor or CommitExtractor()
        extracted = extractor.extract(repo, author_handle, max_commits=max_commits)
        return self.extract_from_commits(extracted.commits)

