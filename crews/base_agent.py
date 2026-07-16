"""Base agent interface, registry, and optional LLM-backed run wrapper."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from schemas.decision_objects import AgentMessage, RiskDecisionObject


@dataclass
class AgentResult:
    success: bool
    message: str
    decision_object: Optional[RiskDecisionObject] = None
    metadata: Dict[str, Any] | None = None


class Agent:
    name: str = "base-agent"
    role: str = "base"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError


REGISTRY: Dict[str, Agent] = {}


def register(agent: Agent) -> Agent:
    REGISTRY[agent.name] = agent
    return agent


def get(name: str) -> Agent:
    return REGISTRY[name]


def llm_enabled() -> bool:
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "infra", "config.yaml")
    if not os.path.exists(cfg_path):
        return False
    try:
        import yaml  # type: ignore

        with open(cfg_path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        return bool(cfg.get("llm", {}).get("enabled", False))
    except Exception:
        return False


def kimi_client() -> Optional[Any]:
    if not llm_enabled():
        return None
    if os.getenv("MOONSHOT_API_KEY"):
        from infra.kimi_client import KimiClient  # type: ignore

        return KimiClient()
    return None
