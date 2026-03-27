from __future__ import annotations

import json
from typing import Protocol

from techwill.models import WarningSignal


class LLMClientLike(Protocol):
    def complete(self, *, system_prompt: str, user_prompt: str) -> str: ...


class WarningSeverityAnalyzer:
    """Classify warning severities with an LLM in a single pass."""

    def __init__(self, llm_client: LLMClientLike) -> None:
        self.llm_client = llm_client

    def classify(self, warnings: list[WarningSignal]) -> list[WarningSignal]:
        if not warnings:
            return warnings

        payload = [
            {"index": i, "text": w.text, "context": w.context}
            for i, w in enumerate(warnings)
        ]
        response = self.llm_client.complete(
            system_prompt=(
                "Classify software delivery risk severity. "
                "Return strict JSON: {\"severities\":[\"high|medium|low\", ...]} matching input order."
            ),
            user_prompt=f"Warnings:\n{json.dumps(payload, indent=2)}",
        )

        try:
            parsed = json.loads(response)
            severities = parsed.get("severities", [])
            if not isinstance(severities, list) or len(severities) != len(warnings):
                return warnings
            for warning, sev in zip(warnings, severities):
                sev_norm = str(sev).strip().lower()
                if sev_norm in {"high", "medium", "low"}:
                    warning.severity = sev_norm
            return warnings
        except Exception:
            return warnings

