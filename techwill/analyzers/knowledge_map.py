from __future__ import annotations

from collections import defaultdict

from techwill.models import CommitRecord


class KnowledgeMapAnalyzer:
    """Find files where an author has exclusive/primary knowledge."""

    def __init__(self, *, dominance_threshold: float = 0.60, max_other_contributors: int = 1) -> None:
        self.dominance_threshold = dominance_threshold
        self.max_other_contributors = max_other_contributors

    def analyze(
        self,
        *,
        all_commits: list[CommitRecord],
        author_handle: str,
    ) -> list[str]:
        target = author_handle.lower().lstrip("@")
        file_author_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for commit in all_commits:
            author_id = self._normalize_author_id(commit)
            for file_path in commit.files_touched:
                file_author_counts[file_path][author_id] += 1

        exclusive_files: list[str] = []
        for file_path, author_counts in file_author_counts.items():
            total = sum(author_counts.values())
            if total == 0:
                continue

            target_count = 0
            other_contributor_count = 0
            for author_id, count in author_counts.items():
                if target in author_id:
                    target_count += count
                elif count > 0:
                    other_contributor_count += 1

            share = target_count / total
            if share >= self.dominance_threshold and other_contributor_count <= self.max_other_contributors:
                exclusive_files.append(file_path)

        return sorted(set(exclusive_files))

    @staticmethod
    def _normalize_author_id(commit: CommitRecord) -> str:
        name = (commit.author_name or "").strip().lower()
        email = (commit.author_email or "").strip().lower()
        return f"{name}<{email}>"

