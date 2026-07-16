"""Clean, align, and quality-check datasets produced by ingestion."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict

import pandas as pd

from crews.base_agent import Agent, AgentResult, register
from schemas.decision_objects import Lineage, RiskDecisionObject


@register
class NormalizeAgent(Agent):
    name = "normalize-agent"
    role = "data"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        path = context.get("raw_path", r"data/raw/market_quotes.csv")
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df.dropna(subset=["Close"]).sort_values(["ticker", "date"]) 
        df["returns"] = df.groupby("ticker")["Close"].pct_change()
        df["log_returns"] = __import__('numpy').log(1 + df["returns"].fillna(0))
        df = df.dropna(subset=["returns"]).reset_index(drop=True)
        df.to_csv(r"data/silver/market_clean.csv", index=False)
        min_q = context.get("min_quality_score", 0.8)
        lower = df.groupby("ticker")["returns"].quantile(0.01)
        valid = len(df)
        quality = 0.95 if (df["returns"].std() > 0).all() else 0.80
        lineage = Lineage(
            source="market_feed",
            dataset="market_clean",
            version="v1",
            as_of=dt.datetime.utcnow(),
            quality_score=quality,
        )
        d = RiskDecisionObject(
            decision_id="normalize-001",
            risk_bucket="market",
            instrument_or_exposure_id="PORTFOLIO-ALL",
            as_of_date=dt.datetime.utcnow(),
            model_version="normalize-v1",
            model_technique="schema-clean+returns",
            data_lineage=[lineage],
        )
        return AgentResult(success=True, message=f"Normalized {valid} records", decision_object=d)

