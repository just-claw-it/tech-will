from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from git import Repo

from techwill.models import BranchRecord


@dataclass(slots=True)
class ExtractedBranches:
    abandoned_branches: list[BranchRecord]


class BranchExtractor:
    """Extract likely-abandoned branches authored by a contributor."""

    def extract(self, repo: str, author_handle: str, *, include_remote: bool = True) -> ExtractedBranches:
        local_repo_path, was_cloned = self._ensure_local_repo(repo)
        git_repo = Repo(local_repo_path)
        target = author_handle.lower().lstrip("@")

        try:
            main_shas = set(self._collect_mainline_shas(git_repo))
            branches: list[BranchRecord] = []

            refs = list(git_repo.branches)
            if include_remote:
                refs.extend(git_repo.remote().refs if git_repo.remotes else [])

            seen_names: set[str] = set()
            for ref in refs:
                name = str(ref.name)
                if name in seen_names:
                    continue
                seen_names.add(name)

                if name in {"main", "master"} or name.endswith("/main") or name.endswith("/master"):
                    continue

                commit = ref.commit
                author_name = (commit.author.name or "").lower()
                author_email = (commit.author.email or "").lower()
                if target not in author_name and target not in author_email:
                    continue
                if commit.hexsha in main_shas:
                    continue

                branches.append(
                    BranchRecord(
                        name=name,
                        last_commit_sha=commit.hexsha,
                        last_commit_message=(commit.message or "").strip(),
                        last_commit_date=commit.authored_datetime.isoformat(),
                        merged=False,
                        deleted=False,
                        source_url=None,
                    )
                )

            return ExtractedBranches(abandoned_branches=branches)
        finally:
            if was_cloned:
                shutil.rmtree(local_repo_path, ignore_errors=True)

    @staticmethod
    def _collect_mainline_shas(repo: Repo) -> set[str]:
        for branch_name in ("main", "master"):
            if branch_name in repo.heads:
                return {c.hexsha for c in repo.iter_commits(branch_name)}
        return set()

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

