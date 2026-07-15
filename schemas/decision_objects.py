"""Canonical decision objects exchanged between crews.

Every output produced by an agent must validate against these schemas before
being passed downstream. This enforces typed contracts and traceability.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, confloat, conint


class RiskBucket(str, Enum):
    MARKET = "market"
    CREDIT = "credit"
    LIQUIDITY = "liquidity"
    OPERATIONAL = "operational"
    SYSTEMIC = "systemic"


class DataSource(str, Enum):
    MARKET_FEED = "market_feed"
    FILING = "filing"
    NEWS = "news"
    MACRO = "macro"
    INTERNAL_LEDGER = "internal_ledger"
    REGULATORY = "regulatory"
    SYNTHETIC = "synthetic"


class Lineage(BaseModel):
    source: DataSource
    dataset: str
    version: str
    as_of: datetime
    quality_score: confloat(ge=0, le=1) = Field(description="0-1 data quality score")


class VaRBreakdown(BaseModel):
    """RBI/SBC2-style VaR disclosure components."""
    var_1d_99: float = Field(description="1-day 99% VaR in reporting currency")
    var_10d_99: float = Field(description="10-day 99% VaR")
    es_1d_99: float = Field(description="1-day 99% Expected Shortfall")
    es_10d_99: float = Field(description="10-day 99% Expected Shortfall")


class LiquidityMetrics(BaseModel):
    """RBI ALCO-relevant metric subset."""
    lcr: Optional[confloat(ge=0)] = None
    nsfr: Optional[confloat(ge=0)] = None
    net_cumulative_outflow_30d: Optional[float] = None
    available_stable_funding: Optional[float] = None
    required_stable_funding: Optional[float] = None


class StressImpact(BaseModel):
    scenario_name: str
    shock_description: str
    estimated_pnl_impact: float
    estimated_capital_impact: float
    limit_breach_detected: bool


class ComplianceFlag(BaseModel):
    regulation: str
    article_or_circular: str
    reference_url: Optional[str] = None
    status: str
    remediation: Optional[str] = None


class RiskDecisionObject(BaseModel):
    """Structured financial risk decision object that travels across crews."""
    decision_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    risk_bucket: RiskBucket = RiskBucket.MARKET
    instrument_or_exposure_id: str
    as_of_date: datetime
    var_breakdown: Optional[VaRBreakdown] = None
    liquidity_metrics: Optional[LiquidityMetrics] = None
    stress_scenarios: List[StressImpact] = Field(default_factory=list)
    model_version: str
    model_technique: str
    confidence: Optional[confloat(ge=0, le=1)] = None
    data_lineage: List[Lineage] = Field(default_factory=list)
    compliance_flags: List[ComplianceFlag] = Field(default_factory=list)
    explanation: Optional[str] = None
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    audit_hash: Optional[str] = None


class BacktestResult(BaseModel):
    decision_object_id: str
    evaluation_date: datetime
    tested_model_version: str
    sample_size: conint(ge=1)
    violation_rate: confloat(ge=0)
    expected_violation_rate: float
    kupiec_pvalue: Optional[confloat(ge=0, le=1)] = None
    christoffersen_pvalue: Optional[confloat(ge=0, le=1)] = None
    regulatory_status: str = Field(description="pass/fail/conditional per RBI backtesting rules")
    notes: Optional[str] = None


class AgentMessage(BaseModel):
    sender: str
    recipient: str
    task: str
    context: Dict[str, Any] = Field(default_factory=dict)
    decision_object: Optional[RiskDecisionObject] = None
    trace_id: Optional[str] = None
