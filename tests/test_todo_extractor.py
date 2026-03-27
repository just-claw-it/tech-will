from __future__ import annotations

from pathlib import Path

from git import Actor, Repo

from techwill.extractors.commits import CommitExtractor
from techwill.extractors.todos import TodoExtractor


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


def test_todo_extractor_collects_only_target_author_todos(tmp_path: Path) -> None:
    repo = Repo.init(tmp_path)

    _commit_file(
        repo,
        tmp_path / "src" / "one.py",
        "x = 1\n# TODO: tighten edge case\n",
        "parser update",
        author_name="Alice Example",
        author_email="alice@example.com",
    )
    _commit_file(
        repo,
        tmp_path / "src" / "two.py",
        "y = 2\n# FIXME: remove hardcoded value\n",
        "temp workaround",
        author_name="Alice Example",
        author_email="alice@example.com",
    )
    _commit_file(
        repo,
        tmp_path / "src" / "three.py",
        "z = 3\n# TODO: bob's task\n",
        "other author commit",
        author_name="Bob Example",
        author_email="bob@example.com",
    )

    todos = TodoExtractor().extract(
        str(tmp_path),
        "alice",
        commit_extractor=CommitExtractor(),
    )

    assert len(todos) == 2
    assert {todo.file_path for todo in todos} == {"src/one.py", "src/two.py"}
    assert any("TODO" in todo.text for todo in todos)
    assert any("FIXME" in todo.text for todo in todos)

