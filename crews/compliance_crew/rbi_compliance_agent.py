"""Compliance agent checking outputs against RBI/SBC2 guidance."""
from __future__ import annotations

from typing import Any, Dict

from crews.base_agent import Agent, AgentResult, register
from schemas.decision_objects import (
    ComplianceFlag,
    Lineage,
    RiskBucket,
    RiskDecisionObject,
)


@register
class RBIComplianceAgent(Agent):
    name = "rbi-compliance-agent"
    role = "compliance"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        do: RiskDecisionObject = context.get("decision_object")
        flags = []
        regs = [
            ComplianceFlag(
                regulation="RBI_Master_Direction_NBFC",
                article_or_circular="Risk Management Framework para 14.2",
                status="pending_lineage_gap_check",
            ),
            ComplianceFlag(
                regulation="SBC2_VaR",
                article_or_circular="Historical VaR backtesting + 3-zone coloring",
                status="pending_backtest",
            ),
            ComplianceFlag(
                regulation="Basel_III_Market_Risk",
                article_or_circular="FRTB equivalent stressed VaR bucket boundary",
                status="pending_stress",
            ),
        ]
        if do:
            missing = [s for s in do.data_lineage if s.quality_score < 0.8]
            if missing:
                regs[0].status = "failed"
                regs[0].remediation = "Improve data quality score below 0.8 before acceptance"
            if do.var_breakdown and abs(do.var_breakdown.var_10d_99) > 0.06:
                regs[1].status = "failed"
                regs[1].remediation = "10-d VaR above 6%; requires stress test and limit review"
            flags = regs
        d = RiskDecisionObject(
            decision_id="compliance-check-001",
            risk_bucket=RiskBucket.MARKET,
            instrument_or_exposure_id="PORTFOLIO-ALL",
            as_of_date=do.as_of_date if do else __import__('datetime').datetime.utcnow(),
            model_version="rulebook-v1",
            model_technique="RBI-compliance-rules",
            data_lineage=do.data_lineage if do else [],
            compliance_flags=flags,
            explanation="Automated rulebook check against RBI/SBC2/Basel III criteria",
        )
        return AgentResult(success=True, message="Compliance check completed", decision_object=d)

