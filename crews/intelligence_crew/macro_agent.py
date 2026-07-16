"""Macro and regime indicator agent.
Produces a quantitative regime label and, if enabled, a Kimi-backed narrative.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from crews.base_agent import Agent, AgentResult, kimi_client, llm_enabled, register
from crews.prompts import MACRO_REGIME_PROMPT
from schemas.decision_objects import Lineage, RiskDecisionObject


LOGGER = logging.getLogger("market-risk.macro")


def _llm_explanation(vol: float, cagr: float, regime: str) -> Optional[str]:
    client = kimi_client()
    if client is None:
        return None
    messages = [
        {"role": "system", "content": MACRO_REGIME_PROMPT},
        {
            "role": "user",
            "content": f"annualized_volatility={vol:.4%}, 1y_cagr={cagr:.4%}, rule_regime={regime}",
        },
    ]
    try:
        return client.chat(messages=messages, temperature=0.2)
    except Exception as exc:
        LOGGER.warning("Kimi explanation failed: %s", exc)
        return None


@register
class MacroRegimeAgent(Agent):
    name = "macro-regime-agent"
    role = "intelligence"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        path = context.get("clean_path", r"data/silver/market_clean.parquet")
        df = pd.read_parquet(path)
        nsei = df.loc[df["ticker"] == "^NSEI", ["date", "returns"]].dropna().sort_values("date").tail(252)
        if nsei.empty:
            return AgentResult(success=False, message="Missing index returns for regime detection")
        vol = float(nsei["returns"].std() * np.sqrt(252))
        cagr = float((1 + nsei["returns"]).prod() ** (252 / len(nsei)) - 1)
        regime = "high_vol" if vol > 0.22 else "normal" if vol > 0.12 else "low_vol"

        explanation = _llm_explanation(vol=vol, cagr=cagr, regime=regime) if llm_enabled() else None
        lineage = Lineage(
            source="market_feed",
            dataset="macro_regime_v1",
            version="v1",
            as_of=dt.datetime.utcnow(),
            quality_score=0.9,
        )
        d = RiskDecisionObject(
            decision_id=f"macro-{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            risk_bucket="market",
            instrument_or_exposure_id="^NSEI",
            as_of_date=dt.datetime.utcnow(),
            model_version="macro-regime-v1",
            model_technique="volatility-threshold",
            confidence=0.75,
            data_lineage=[lineage],
            explanation=explanation or f"regime={regime}, annualized vol={vol:.2%}, cagr={cagr:.2%}",
        )
        return AgentResult(success=True, message=f"Regime detected: {regime}", decision_object=d)

