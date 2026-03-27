from __future__ import annotations

import json

from techwill.analyzers.warning_severity import WarningSeverityAnalyzer
from techwill.models import WarningSignal


class _FakeLLM:
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        assert "strict JSON" in system_prompt
        assert "Warnings:" in user_prompt
        return json.dumps({"severities": ["high", "low"]})


def test_warning_severity_classifies_warning_levels() -> None:
    warnings = [
        WarningSignal(text="this will break", context="Issue #1"),
        WarningSignal(text="be careful", context="PR #2"),
    ]
    updated = WarningSeverityAnalyzer(_FakeLLM()).classify(warnings)
    assert [w.severity for w in updated] == ["high", "low"]

