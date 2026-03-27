from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


@dataclass(slots=True)
class OutputConfig:
    dir: str = "."
    format: str = "markdown"


@dataclass(slots=True)
class ExtractionConfig:
    max_commits: int = 1000
    warning_keywords: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TechWillConfig:
    output: OutputConfig = field(default_factory=OutputConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)


def load_config(config_path: str | Path | None) -> TechWillConfig:
    path = Path(config_path) if config_path else Path("techwill.yaml")
    if not path.exists():
        return TechWillConfig()

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    expanded = _expand_env_in_obj(raw)

    output = expanded.get("output", {}) if isinstance(expanded, dict) else {}
    extraction = expanded.get("extraction", {}) if isinstance(expanded, dict) else {}
    return TechWillConfig(
        output=OutputConfig(
            dir=str(output.get("dir", ".")),
            format=str(output.get("format", "markdown")),
        ),
        extraction=ExtractionConfig(
            max_commits=int(extraction.get("max_commits", 1000)),
            warning_keywords=list(extraction.get("warning_keywords", [])),
        ),
    )


def _expand_env_in_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand_env_in_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_in_obj(v) for v in value]
    if isinstance(value, str):
        return _expand_env_in_str(value)
    return value


def _expand_env_in_str(value: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.getenv(var_name, "")

    return _ENV_VAR_PATTERN.sub(_replace, value)

