from __future__ import annotations

from pathlib import Path

from techwill.config import load_config


def test_load_config_reads_defaults_when_missing(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "missing.yaml")
    assert cfg.output.dir == "."
    assert cfg.output.format == "markdown"
    assert cfg.extraction.max_commits == 1000


def test_load_config_reads_yaml_and_expands_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MY_OUTPUT_DIR", str(tmp_path / "wills"))
    cfg_path = tmp_path / "techwill.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "output:",
                "  dir: ${MY_OUTPUT_DIR}",
                "  format: both",
                "extraction:",
                "  max_commits: 250",
                "  warning_keywords:",
                "    - temporary fix",
            ]
        ),
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)
    assert cfg.output.dir == str(tmp_path / "wills")
    assert cfg.output.format == "both"
    assert cfg.extraction.max_commits == 250
    assert cfg.extraction.warning_keywords == ["temporary fix"]

