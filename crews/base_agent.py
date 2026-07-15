"""Base agent interface and simple registry.

Agents expose a `run(task, context)` method and produce audited outputs.
"""
from __future__ import annotations

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
