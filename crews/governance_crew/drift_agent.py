"""Drift + kill-switch meta-agent for agent output and model distribution stability."""
from __future__ import annotations

from typing import Any, Dict

from crews.base_agent import Agent, AgentResult, register
from schemas.decision_objects import Lineage, RiskDecisionObject, RiskBucket


@register
class DriftAgent(Agent):
    name = "drift-agent"
    role = "governance"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        do = context.get("decision_object")
        if not do:
            return AgentResult(success=False, message="Missing decision object")
        flags = []
        if (do.confidence or 0) < 0.5:
            flags.append("low_confidence_decision")
        if any((l.quality_score or 0) < 0.75 for l in do.data_lineage):
            flags.append("low_data_quality")
        kill = any(f in flags for f in ["low_confidence_decision"]) or len(flags) >= 2
        lineage = Lineage(
            source="regulatory",
            dataset="drift_monitor",
            version="v1",
            as_of=do.as_of_date,
            quality_score=0.99,
        )
        d = RiskDecisionObject(
            decision_id="drift-001",
            risk_bucket=do.risk_bucket,
            instrument_or_exposure_id=do.instrument_or_exposure_id,
            as_of_date=do.as_of_date,
            var_breakdown=do.var_breakdown,
            liquidity_metrics=do.liquidity_metrics,
            stress_scenarios=do.stress_scenarios,
            model_version="drift-v1",
            model_technique="threshold",
            data_lineage=do.data_lineage + [lineage],
            compliance_flags=do.compliance_flags,
            explanation="Meta-monitoring of decision quality",
            requires_approval=kill or do.requires_approval,
        )
        reason = "Triggers=" + ",".join(flags) if flags else "clean"
        return AgentResult(success=True, message=reason, decision_object=d)

