from __future__ import annotations

from pathlib import Path

from git import Actor, Repo

from techwill.extractors.branches import BranchExtractor


def _commit_file(
    repo: Repo,
    file_path: Path,
    content: str,
    message: str,
    *,
    author_name: str,
    author_email: str,
) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    repo.index.add([str(file_path.relative_to(repo.working_tree_dir))])
    actor = Actor(author_name, author_email)
    repo.index.commit(message=message, author=actor, committer=actor)


def test_branch_extractor_detects_unmerged_author_branch(tmp_path: Path) -> None:
    repo = Repo.init(tmp_path)

    _commit_file(
        repo,
        tmp_path / "base.txt",
        "base\n",
        "initial",
        author_name="Alice Example",
        author_email="alice@example.com",
    )

    feature = repo.create_head("feature/alice-intent")
    repo.head.reference = feature
    repo.head.reset(index=True, working_tree=True)

    _commit_file(
        repo,
        tmp_path / "feature.txt",
        "feature work\n",
        "workaround for parser edge",
        author_name="Alice Example",
        author_email="alice@example.com",
    )

    # Move back to default branch (left feature branch unmerged).
    default_branch_name = "main" if "main" in repo.heads else "master"
    repo.head.reference = repo.heads[default_branch_name]
    repo.head.reset(index=True, working_tree=True)

    result = BranchExtractor().extract(str(tmp_path), "alice", include_remote=False)

    assert len(result.abandoned_branches) == 1
    record = result.abandoned_branches[0]
    assert record.name == "feature/alice-intent"
    assert "workaround" in record.last_commit_message

