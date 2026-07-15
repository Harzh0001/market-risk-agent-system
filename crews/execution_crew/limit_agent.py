"""Limit enforcement agent: exposure vs authorized desks/loss triggers."""
from __future__ import annotations

from typing import Any, Dict

from crews.base_agent import Agent, AgentResult, register
from schemas.decision_objects import Lineage, RiskDecisionObject, StressImpact


@register
class LimitAgent(Agent):
    name = "limit-agent"
    role = "execution"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        do = context.get("decision_object")
        if not do:
            return AgentResult(success=False, message="Missing decision object")
        breach = False
        notes = []
        if do.var_breakdown:
            if abs(do.var_breakdown.var_10d_99) > 0.06:
                breach = True
                notes.append("10D VaR breach: >6%")
        if do.liquidity_metrics:
            lcr = do.liquidity_metrics.lcr or 0
            if lcr < 1.0:
                breach = True
                notes.append(f"LCR breach: {lcr:.2f}")
        stress = []
        if do.stress_scenarios:
            worst = max(do.stress_scenarios, key=lambda x: x.estimated_pnl_impact)
            if worst.estimated_capital_impact < -1e8:
                breach = True
                notes.append("Stress capital impact exceeds INR 10 crore")
            stress.append(worst)
        lineage = Lineage(
            source="internal_ledger",
            dataset="limit_checks",
            version="v1",
            as_of=do.as_of_date,
            quality_score=0.95,
        )
        d = RiskDecisionObject(
            decision_id="limit-check-001",
            risk_bucket=do.risk_bucket,
            instrument_or_exposure_id=do.instrument_or_exposure_id,
            as_of_date=do.as_of_date,
            var_breakdown=do.var_breakdown,
            liquidity_metrics=do.liquidity_metrics,
            stress_scenarios=stress,
            model_version="rule-v1",
            model_technique="threshold-watch",
            data_lineage=do.data_lineage + [lineage],
            compliance_flags=do.compliance_flags,
            explanation="; ".join(notes) if notes else "No limit breaches",
            requires_approval=breach or do.requires_approval,
        )
        return AgentResult(success=True, message="Limit check completed", decision_object=d)

