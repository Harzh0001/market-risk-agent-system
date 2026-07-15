"""RBI-relevant market risk factor model: systematic + idiosyncratic decomposition."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from crews.base_agent import Agent, AgentResult, register
from schemas.decision_objects import Lineage, RiskDecisionObject, RiskBucket


@register
class FactorModelAgent(Agent):
    name = "factor-model-agent"
    role = "modeling"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        path = context.get("clean_path", r"data/silver/market_clean.parquet")
        df = pd.read_parquet(path)
        ticker = context.get("ticker", "^NSEI")
        window = int(context.get("window", 252))
        sub = df.loc[df["ticker"].isin(["^NSEI", "INR=X", ticker]), ["date", "ticker", "returns"]].dropna()
        sub = sub.pivot(index="date", columns="ticker", values="returns").tail(window).dropna()
        if sub.shape[0] < 60:
            return AgentResult(success=False, message="Not enough factor overlap")
        X = sub[["^NSEI", "INR=X"]].values
        y = sub[ticker].values
        lr = LinearRegression().fit(X, y)
        resid = y - lr.predict(X)
        systematic_var = np.var(lr.predict(X))
        idiosyncratic_var = np.var(resid)
        lineage = Lineage(
            source="market_feed",
            dataset=f"factor_model_v1:{ticker}",
            version="v1",
            as_of=dt.datetime.utcnow(),
            quality_score=0.84,
        )
        d = RiskDecisionObject(
            decision_id=f"factor-{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            risk_bucket=RiskBucket.MARKET,
            instrument_or_exposure_id=ticker,
            as_of_date=dt.datetime.utcnow(),
            model_version="ols-2factor",
            model_technique="linear-factor-decomp",
            data_lineage=[lineage],
            explanation=f"R2={lr.score(X,y):.3f}; systematic={systematic_var:.4f}, idiosyncratic={idiosyncratic_var:.4f}",
        )
        return AgentResult(success=True, message=f"Factor model computed for {ticker}", decision_object=d)

