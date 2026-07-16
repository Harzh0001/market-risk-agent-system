"""Backtest historical VaR with Kupiec and Christoffersen interval tests."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy import stats

from crews.base_agent import Agent, AgentResult, register
from schemas.decision_objects import (
    BacktestResult,
    Lineage,
    RiskDecisionObject,
    VaRBreakdown,
)


@register
class BacktesterAgent(Agent):
    name = "backtester-agent"
    role = "modeling"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        path = context.get("clean_path", r"data/silver/market_clean.csv")
        df = pd.read_csv(path)
        ticker = context.get("ticker", "^NSEI")
        window = int(context.get("backtest_window", 500))
        confidence = float(context.get("confidence", 0.99))
        rets = df.loc[df["ticker"] == ticker, "returns"].dropna().tail(window)
        if len(rets) < 60:
            return AgentResult(success=False, message="Not enough data for backtest")
        var_q = float(rets.quantile(1 - confidence))
        violations = (rets < var_q).astype(int)
        n = len(rets)
        x = int(violations.sum())
        p_hat = x / n
        p0 = 1 - confidence
        if 0 < p_hat < 1:
            kupiec = -2 * np.log(
                (p0**x) * ((1 - p0)**(n - x)) / ((p_hat**x) * ((1 - p_hat)**(n - x)))
            )
            kupiec_p = float(1 - stats.chi2.cdf(kupiec, 1))
        else:
            kupiec_p = 0.0
        # Christoffersen independence test
        prev = None
        n00 = n11 = n01 = n10 = 0
        for v in violations:
            if prev is None:
                prev = v
                continue
            if prev == 0 and v == 0:
                n00 += 1
            elif prev == 1 and v == 1:
                n11 += 1
            elif prev == 0 and v == 1:
                n01 += 1
            else:
                n10 += 1
            prev = v
        pi0 = (n00 + n01) / max(1, n00 + n01 + n10)
        pi1 = (n10 + n11) / max(1, n10 + n11 + n01)
        pi = (n01 + n10) / max(1, n)
        if 0 < pi < 1 and 0 < pi0 < 1 and 0 < pi1 < 1:
            lr_ind = -2 * np.log(
                ((1 - pi)**(n01 + n10)) * (pi**(n00 + n11))
                / (((1 - pi0)**n01) * (pi0**n00) * ((1 - pi1)**n10) * (pi1**n11))
            )
            christ_p = float(1 - stats.chi2.cdf(lr_ind, 1))
        else:
            christ_p = 0.0
        status = "pass" if kupiec_p > 0.05 and christ_p > 0.05 else "conditional"
        if (x / n) > 2 * (1 - confidence):
            status = "fail"
        lineage = Lineage(
            source="internal_ledger",
            dataset=f"backtest_v1:{ticker}",
            version="v1",
            as_of=dt.datetime.utcnow(),
            quality_score=0.86,
        )
        d = RiskDecisionObject(
            decision_id=f"backtest-{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            risk_bucket="market",
            instrument_or_exposure_id=ticker,
            as_of_date=dt.datetime.utcnow(),
            var_breakdown=VaRBreakdown(
                var_1d_99=var_q,
                var_10d_99=float(var_q * np.sqrt(10)),
                es_1d_99=float(rets[rets <= var_q].mean()),
                es_10d_99=float(rets[rets <= var_q].mean() * np.sqrt(10)),
            ),
            model_version="backtest-engine",
            model_technique="kupiec+christoffersen",
            data_lineage=[lineage],
            explanation=f"violations={x}/{n}={p_hat:.2%}; kupiec={kupiec_p:.3f}; christ={christ_p:.3f}",
        )
        bt = BacktestResult(
            decision_object_id=d.decision_id,
            evaluation_date=dt.datetime.utcnow(),
            tested_model_version="historical-simulation",
            sample_size=n,
            violation_rate=p_hat,
            expected_violation_rate=1 - confidence,
            kupiec_pvalue=kupiec_p,
            christoffersen_pvalue=christ_p,
            regulatory_status=status,
            notes="conditional when one test and not the other; fail when excess violations.",
        )
        return AgentResult(
            success=True,
            message=f"Backtest completed: status={status}",
            decision_object=d,
            metadata={"backtest_result": bt.model_dump()},
        )
