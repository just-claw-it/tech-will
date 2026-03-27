from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from git import Repo

from techwill.models import CommitRecord, TodoComment

DEFAULT_RISK_KEYWORDS: tuple[str, ...] = (
    "temp",
    "hack",
    "fixme",
    "revisit",
    "workaround",
)
TODO_PATTERN = re.compile(r"\b(TODO|FIXME)\b", flags=re.IGNORECASE)


@dataclass(slots=True)
class ExtractedCommits:
    commits: list[CommitRecord]
    repo_path: str
    was_cloned: bool


class CommitExtractor:
    """Extract commits authored by a handle from a local or GitHub repo."""

    def __init__(self, risk_keywords: list[str] | None = None) -> None:
        self.risk_keywords = tuple((risk_keywords or list(DEFAULT_RISK_KEYWORDS)))

    def extract(
        self,
        repo: str,
        author_handle: str,
        *,
        max_commits: int | None = None,
    ) -> ExtractedCommits:
        local_repo_path, was_cloned = self._ensure_local_repo(repo)
        git_repo = Repo(local_repo_path)
        commit_records: list[CommitRecord] = []

        try:
            for commit in git_repo.iter_commits("--all", max_count=max_commits):
                if not self._author_matches(commit.author.name, commit.author.email, author_handle):
                    continue

                message = commit.message.strip()
                todo_additions = self._extract_todo_fixme_additions(git_repo, commit.hexsha)
                risks = self._extract_risk_keywords(message)
                commit_records.append(
                    CommitRecord(
                        sha=commit.hexsha,
                        message=message,
                        authored_date=commit.authored_datetime.isoformat(),
                        author_name=commit.author.name or "",
                        author_email=commit.author.email or "",
                        html_url=None,
                        files_touched=self._extract_files_touched(git_repo, commit.hexsha),
                        todo_fixme_additions=todo_additions,
                        risk_keywords_found=risks,
                    )
                )
        finally:
            if was_cloned:
                shutil.rmtree(local_repo_path, ignore_errors=True)

        return ExtractedCommits(commits=commit_records, repo_path=local_repo_path, was_cloned=was_cloned)

    def _extract_todo_fixme_additions(self, repo: Repo, commit_sha: str) -> list[TodoComment]:
        raw_patch = repo.git.show(commit_sha, "--pretty=format:", "--unified=0")
        file_path = ""
        todos: list[TodoComment] = []

        for line in raw_patch.splitlines():
            if line.startswith("+++ b/"):
                file_path = line.removeprefix("+++ b/")
                continue
            if not line.startswith("+") or line.startswith("+++"):
                continue
            if TODO_PATTERN.search(line):
                todos.append(
                    TodoComment(
                        commit_sha=commit_sha,
                        file_path=file_path or "<unknown>",
                        text=line[1:].strip(),
                    )
                )

        return todos

    def _extract_risk_keywords(self, message: str) -> list[str]:
        lowered = message.lower()
        return [kw for kw in self.risk_keywords if kw.lower() in lowered]

    @staticmethod
    def _extract_files_touched(repo: Repo, commit_sha: str) -> list[str]:
        names = repo.git.show(commit_sha, "--pretty=format:", "--name-only").splitlines()
        cleaned = [line.strip() for line in names if line.strip()]
        return sorted(set(cleaned))

    @staticmethod
    def _author_matches(author_name: str | None, author_email: str | None, handle: str) -> bool:
        normalized_handle = handle.lower().strip().removeprefix("@")
        possible_values = (
            (author_name or "").lower(),
            (author_email or "").lower(),
        )
        return any(normalized_handle in value for value in possible_values)

    @staticmethod
    def _ensure_local_repo(repo: str) -> tuple[str, bool]:
        if os.path.isdir(repo):
            return str(Path(repo).resolve()), False
        if repo.startswith(("https://", "git@")):
            clone_url = repo
        else:
            clone_url = f"https://github.com/{repo}.git"
        temp_dir = tempfile.mkdtemp(prefix="techwill-repo-")
        Repo.clone_from(clone_url, temp_dir)
        return temp_dir, True

