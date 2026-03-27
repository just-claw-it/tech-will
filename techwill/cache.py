from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from techwill.models import (
    BranchRecord,
    CommitRecord,
    ContributionProfile,
    IssueRecord,
    PRRecord,
    ReviewComment,
    TodoComment,
    UnfinishedItem,
    WarningSignal,
)


class ProfileCache:
    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path(".techwill-cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def key(self, *, repo: str, author: str, max_commits: int) -> str:
        raw = f"{repo}|{author.lower().lstrip('@')}|{max_commits}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    def load(self, *, repo: str, author: str, max_commits: int) -> ContributionProfile | None:
        path = self.cache_dir / f"{self.key(repo=repo, author=author, max_commits=max_commits)}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return self._from_dict(payload)

    def save(self, profile: ContributionProfile, *, max_commits: int) -> Path:
        path = self.cache_dir / f"{self.key(repo=profile.repo, author=profile.author_handle, max_commits=max_commits)}.json"
        path.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")
        return path

    def _from_dict(self, payload: dict) -> ContributionProfile:
        profile = ContributionProfile(
            author_handle=payload["author_handle"],
            repo=payload["repo"],
            commits=[self._commit(x) for x in payload.get("commits", [])],
            prs_authored=[self._pr(x) for x in payload.get("prs_authored", [])],
            issues_opened=[self._issue(x) for x in payload.get("issues_opened", [])],
            review_comments=[ReviewComment(**x) for x in payload.get("review_comments", [])],
            todo_comments=[TodoComment(**x) for x in payload.get("todo_comments", [])],
            abandoned_branches=[BranchRecord(**x) for x in payload.get("abandoned_branches", [])],
            warning_signals=[WarningSignal(**x) for x in payload.get("warning_signals", [])],
            unfinished_items=[UnfinishedItem(**x) for x in payload.get("unfinished_items", [])],
            exclusive_files=list(payload.get("exclusive_files", [])),
            bus_factor_modules=list(payload.get("bus_factor_modules", [])),
        )
        return profile

    @staticmethod
    def _commit(payload: dict) -> CommitRecord:
        todos = [TodoComment(**x) for x in payload.get("todo_fixme_additions", [])]
        return CommitRecord(
            sha=payload["sha"],
            message=payload["message"],
            authored_date=payload["authored_date"],
            author_name=payload["author_name"],
            author_email=payload["author_email"],
            html_url=payload.get("html_url"),
            files_touched=list(payload.get("files_touched", [])),
            todo_fixme_additions=todos,
            risk_keywords_found=list(payload.get("risk_keywords_found", [])),
        )

    @staticmethod
    def _pr(payload: dict) -> PRRecord:
        comments = [ReviewComment(**x) for x in payload.get("unresolved_review_comments", [])]
        return PRRecord(
            number=payload["number"],
            title=payload["title"],
            state=payload["state"],
            merged=payload["merged"],
            url=payload["url"],
            unresolved_review_comments=comments,
        )

    @staticmethod
    def _issue(payload: dict) -> IssueRecord:
        return IssueRecord(
            number=payload["number"],
            title=payload["title"],
            state=payload["state"],
            url=payload["url"],
            body=payload.get("body", ""),
            comments=list(payload.get("comments", [])),
        )

