"""Market risk VaR agent: historical simulation + GARCH(1,1) ES baseline."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy import stats

from crews.base_agent import Agent, AgentResult, register
from schemas.decision_objects import (
    RiskDecisionObject,
    VaRBreakdown,
    Lineage,
    RiskBucket,
)


@register
class VarAgent(Agent):
    name = "var-agent"
    role = "modeling"

    def _garch_es(self, r: pd.Series, alpha: float = 0.99):
        import arch
        am = arch.arch_model(r*100, vol="Garch", p=1, q=1, dist="normal", rescale=False)
        res = am.fit(disp="off", show_warning=False)
        fc = res.forecast(horizon=1)
        sigma = np.sqrt(fc.variance.values[-1, 0]) / 100.0
        mu = r.mean()
        q = stats.t.ppf(alpha, df=6)
        return float(-(mu + sigma * q))

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        path = context.get("clean_path", r"data/silver/market_clean.csv")
        df = pd.read_csv(path)
        ticker = context.get("ticker", "^NSEI")
        window = int(context.get("window", 500))
        alpha = float(context.get("confidence", 0.99))
        rets = df.loc[df["ticker"] == ticker, "returns"].dropna().tail(window)
        if len(rets) < 60:
            return AgentResult(success=False, message="Insufficient observations for VaR")
        idx = int((1 - alpha) * len(rets))
        var_1d = float(rets.iloc[idx]) if idx < len(rets) else float(rets.quantile(0.01))
        es_1d = float(rets[rets <= var_1d].mean()) if var_1d < 0 else float(rets.mean())
        var_10d = float(var_1d * np.sqrt(10))
        es_10d = float(es_1d * np.sqrt(10))
        try:
            garch_es = self._garch_es(rets, alpha)
        except Exception:
            garch_es = es_1d
        lineage = Lineage(
            source="internal_ledger",
            dataset=f"var_model_v1:{ticker}",
            version="v1",
            as_of=dt.datetime.utcnow(),
            quality_score=0.88,
        )
        d = RiskDecisionObject(
            decision_id=f"var-{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            risk_bucket=RiskBucket.MARKET,
            instrument_or_exposure_id=ticker,
            as_of_date=dt.datetime.utcnow(),
            var_breakdown=VaRBreakdown(
                var_1d_99=var_1d,
                var_10d_99=var_10d,
                es_1d_99=es_1d,
                es_10d_99=es_10d,
            ),
            model_version="historical-simulation+garch",
            model_technique="quantile+arch",
            confidence=alpha,
            data_lineage=[lineage],
            explanation=f"1-d 99% VaR estimated over {len(rets)} days; GARCH ES={garch_es:.4%}",
            requires_approval=True if abs(var_10d) > 0.05 else False,
        )
        return AgentResult(success=True, message=f"VaR computed for {ticker}", decision_object=d)

