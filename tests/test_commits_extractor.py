from __future__ import annotations

from pathlib import Path

from git import Actor, Repo

from techwill.extractors.commits import CommitExtractor


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


def test_extract_commits_filters_by_author_and_detects_signals(tmp_path: Path) -> None:
    repo = Repo.init(tmp_path)

    _commit_file(
        repo,
        tmp_path / "a.py",
        "print('hello')\n# TODO: tighten validation\n",
        "temporary fix: parser workaround",
        author_name="Alice Example",
        author_email="alice@example.com",
    )
    _commit_file(
        repo,
        tmp_path / "b.py",
        "print('world')\n# TODO: this should not count for alice\n",
        "regular commit",
        author_name="Bob Example",
        author_email="bob@example.com",
    )

    extracted = CommitExtractor().extract(str(tmp_path), "alice")

    assert len(extracted.commits) == 1
    commit = extracted.commits[0]
    assert "temporary fix" in commit.message
    assert "temp" in commit.risk_keywords_found
    assert "workaround" in commit.risk_keywords_found
    assert len(commit.todo_fixme_additions) == 1
    assert "TODO" in commit.todo_fixme_additions[0].text
    assert commit.todo_fixme_additions[0].file_path == "a.py"

