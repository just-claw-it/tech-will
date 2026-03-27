from __future__ import annotations

from pathlib import Path

from techwill.cache import ProfileCache
from techwill.models import ContributionProfile


def test_profile_cache_roundtrip(tmp_path: Path) -> None:
    cache = ProfileCache(tmp_path / ".cache")
    profile = ContributionProfile(author_handle="alice", repo="owner/repo")
    profile.exclusive_files = ["src/a.py"]

    cache.save(profile, max_commits=100)
    loaded = cache.load(repo="owner/repo", author="alice", max_commits=100)

    assert loaded is not None
    assert loaded.author_handle == "alice"
    assert loaded.exclusive_files == ["src/a.py"]

