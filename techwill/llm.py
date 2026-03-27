from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import request


@dataclass(slots=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 60

    @classmethod
    def from_env(cls) -> "LLMConfig":
        base_url = os.getenv("LLM_BASE_URL", "").strip()
        api_key = os.getenv("LLM_API_KEY", "").strip()
        model = os.getenv("LLM_MODEL", "").strip()
        if not base_url or not api_key or not model:
            raise ValueError("Missing one or more required env vars: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL")
        return cls(base_url=base_url.rstrip("/"), api_key=api_key, model=model)


class OpenAICompatibleClient:
    """Minimal OpenAI-compatible chat-completions client."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        raw = self._post_json(
            url=f"{self.config.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout_seconds=self.config.timeout_seconds,
        )
        return self._extract_content(raw)

    @staticmethod
    def _extract_content(response_json: dict[str, Any]) -> str:
        choices = response_json.get("choices", [])
        if not choices:
            raise ValueError("LLM response missing choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise ValueError("LLM response content is missing or invalid")
        return content.strip()

    @staticmethod
    def _post_json(
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        req = request.Request(
            url=url,
            method="POST",
            headers=headers,
            data=json.dumps(payload).encode("utf-8"),
        )
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("Unexpected LLM response payload")
        return data

