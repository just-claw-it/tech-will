from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_skill_module():
    path = Path(".claude/skills/tech-will/skill.py").resolve()
    spec = importlib.util.spec_from_file_location("tech_will_skill", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_command_normalizes_author_and_output() -> None:
    skill = _load_skill_module()
    cmd = skill.build_command(
        repo="owner/repo",
        author="@alice",
        mode="archaeology",
        output="/tmp/will.md",
        format="both",
        max_commits=500,
    )

    assert cmd[:2] == ["tech-will", "generate"]
    assert "--author" in cmd and "alice" in cmd
    assert "@alice" not in cmd
    assert "--output" in cmd and "/tmp/will.md" in cmd
    assert "--max-commits" in cmd and "500" in cmd

