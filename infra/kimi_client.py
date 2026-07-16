"""Kimi LLM client wrapper.

Uses the OpenAI-compatible Kimi / Moonshot API endpoint.
Backend is selected by env/config:
  - base_url: https://api.moonshot.ai/v1
  - api_key: MOONSHOT_API_KEY
  - model alias: MOONSHOT_MODEL or infra config llm.kimi.model
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LOGGER = logging.getLogger("market-risk.kimi")


class KimiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.moonshot.ai/v1",
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("MOONSHOT_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.model = model or os.getenv("MOONSHOT_MODEL", "kimi-k2.6")
        if not self.api_key:
            raise EnvironmentError("MOONSHOT_API_KEY is not set")
        self.client = OpenAI(api_key=self.api_key, base_url=f"{self.base_url}/")

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        kwargs: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format
        try:
            completion = self.client.chat.completions.create(**kwargs)
            msg = completion.choices[0].message.content or ""
            LOGGER.debug("Kimi tokens prompt=%s completion=%s", getattr(completion.usage, 'prompt_tokens', '?'), getattr(completion.usage, 'completion_tokens', '?'))
            return msg
        except Exception as exc:  # pragma: no cover
            LOGGER.exception("Kimi chat failed: %s", exc)
            raise


def kimi_available() -> bool:
    return bool(os.getenv("MOONSHOT_API_KEY"))
