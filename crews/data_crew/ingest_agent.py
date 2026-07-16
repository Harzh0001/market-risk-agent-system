"""Data ingestion agent for market/risk datasets."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict

import pandas as pd
import yfinance as yf

from crews.base_agent import Agent, AgentResult, register
from schemas.decision_objects import Lineage, RiskDecisionObject, VaRBreakdown


@register
class IngestAgent(Agent):
    name = "ingest-agent"
    role = "data"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        tickers = context.get("tickers", ["^NSEI", "^BSESN", "INR=X"])
        start = context.get("start", "2018-01-01")
        end = context.get("end", dt.date.today().isoformat())
        frames = []
        for t in tickers:
            df = yf.download(t, start=start, end=end, progress=False, auto_adjust=True)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            df = df.reset_index().rename(columns={"Date": "date", "index": "date"})
            df["ticker"] = t
            frames.append(df)
        if not frames:
            return AgentResult(success=False, message="No data downloaded")
        raw = pd.concat(frames, ignore_index=True)
        raw.to_csv(r"data/raw/market_quotes.csv", index=False)
        lineage = Lineage(
            source="market_feed",
            dataset="yfinance_nse_usd",
            version="v1",
            as_of=dt.datetime.utcnow(),
            quality_score=0.92,
        )
        d = RiskDecisionObject(
            decision_id="ingest-001",
            risk_bucket="market",
            instrument_or_exposure_id="PORTFOLIO-ALL",
            as_of_date=dt.datetime.utcnow(),
            model_version="ingest-raw",
            model_technique="yfinance",
            data_lineage=[lineage],
        )
        return AgentResult(success=True, message=f"Ingested {len(raw)} rows", decision_object=d)

