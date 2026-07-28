"""Orchestrator: composes crew runs into a typed workflow for market risk."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from crews.data_crew.ingest_agent import IngestAgent
from crews.data_crew.normalize_agent import NormalizeAgent
from crews.intelligence_crew.macro_agent import MacroRegimeAgent
from crews.intelligence_crew.news_sentiment_agent import NewsSentimentAgent
from crews.modeling_crew.factor_model_agent import FactorModelAgent
from crews.modeling_crew.var_agent import VarAgent
from crews.compliance_crew.rbi_compliance_agent import RBIComplianceAgent
from crews.execution_crew.limit_agent import LimitAgent
from crews.governance_crew.drift_agent import DriftAgent
from schemas.decision_objects import AgentMessage, DataSource, RiskDecisionObject


class MarketRiskOrchestrator:
    def __init__(self) -> None:
        self.ingest = IngestAgent()
        self.normalize = NormalizeAgent()
        self.macro = MacroRegimeAgent()
        self.sentiment = NewsSentimentAgent()
        self.factor = FactorModelAgent()
        self.var = VarAgent()
        self.compliance = RBIComplianceAgent()
        self.limit = LimitAgent()
        self.drift = DriftAgent()

    def run(self, run_date: Optional[str] = None, ticker: str = "^NSEI") -> Dict[str, Any]:
        run_date = run_date or dt.date.today().isoformat()
        trace = {"run_date": run_date, "ticker": ticker, "steps": []}
        ingest_out = self.ingest.run(
            task="ingest market data",
            context={"tickers": list(set(["^NSEI", "^BSESN", "INR=X", ticker])), "end": run_date},
        )
        trace["steps"].append({"agent": "ingest", "success": ingest_out.success})
        if not ingest_out.success:
            return trace

        norm_out = self.normalize.run(task="normalize data", context={"raw_path": r"data/raw/market_quotes.csv"})
        trace["steps"].append({"agent": "normalize", "success": norm_out.success})
        if not norm_out.success:
            return trace

        var_out = self.var.run(task="compute VaR", context={"ticker": ticker, "clean_path": r"data/silver/market_clean.csv"})
        factor_out = self.factor.run(task="factor decomposition", context={"ticker": ticker, "clean_path": r"data/silver/market_clean.csv"})
        macro_out = self.macro.run(task="regime detection", context={"clean_path": r"data/silver/market_clean.csv"})
        sentiment_out = self.sentiment.run(task="news sentiment", context={"ticker": ticker})
        trace["steps"].extend([
            {"agent": "var", "success": var_out.success},
            {"agent": "factor", "success": factor_out.success},
            {"agent": "macro", "success": macro_out.success},
            {"agent": "sentiment", "success": sentiment_out.success},
        ])

        do: Optional[RiskDecisionObject] = None
        if var_out.decision_object:
            do = var_out.decision_object
            do.stress_scenarios = []
            do.explanation = (do.explanation or "") + " | " + (macro_out.decision_object.explanation if macro_out.decision_object else "")
        if factor_out.decision_object:
            do = factor_out.decision_object if do is None else do

        if do is None:
            return trace

        if sentiment_out.decision_object:
            s_obj = sentiment_out.decision_object
            s_label = ""
            s_score = 0.0
            try:
                explanation = s_obj.explanation or ""
                if "sentiment=" in explanation:
                    s_label = explanation.split("sentiment=")[1].split(" ")[0]
                if "score=" in explanation:
                    s_score = float(explanation.split("score=")[1].split(",")[0])
            except Exception:
                s_label = "unknown"
                s_score = 0.0

            if s_label == "positive":
                if do.var_breakdown:
                    old1d = do.var_breakdown.var_1d_99
                    old10d = do.var_breakdown.var_10d_99
                    old_es1d = do.var_breakdown.es_1d_99
                    old_es10d = do.var_breakdown.es_10d_99
                    do.var_breakdown.var_1d_99 = old1d * 1.10 if old1d is not None else old1d
                    do.var_breakdown.var_10d_99 = old10d * 1.10 if old10d is not None else old10d
                    do.var_breakdown.es_1d_99 = old_es1d * 1.10 if old_es1d is not None else old_es1d
                    do.var_breakdown.es_10d_99 = old_es10d * 1.10 if old_es10d is not None else old_es10d
                do.explanation = (do.explanation or "") + " | Sentiment uplift: positive news"
                do.confidence = min((do.confidence or 0.0) + 0.05, 0.99)
            elif s_label == "negative":
                if do.var_breakdown:
                    old1d = do.var_breakdown.var_1d_99
                    old10d = do.var_breakdown.var_10d_99
                    old_es1d = do.var_breakdown.es_1d_99
                    old_es10d = do.var_breakdown.es_10d_99
                    do.var_breakdown.var_1d_99 = old1d * 0.85 if old1d is not None else old1d
                    do.var_breakdown.var_10d_99 = old10d * 0.85 if old10d is not None else old10d
                    do.var_breakdown.es_1d_99 = old_es1d * 0.85 if old_es1d is not None else old_es1d
                    do.var_breakdown.es_10d_99 = old_es10d * 0.85 if old_es10d is not None else old_es10d
                do.explanation = (do.explanation or "") + " | Sentiment downgrade: negative news"
                do.confidence = max((do.confidence or 0.0) - 0.05, 0.01)

        comp_out = self.compliance.run(task="rbi compliance", context={"decision_object": do})
        limit_out = self.limit.run(task="limit check", context={"decision_object": comp_out.decision_object})
        drift_out = self.drift.run(task="drift check", context={"decision_object": limit_out.decision_object})
        trace["steps"].extend([
            {"agent": "compliance", "success": comp_out.success},
            {"agent": "limit", "success": limit_out.success},
            {"agent": "drift", "success": drift_out.success},
        ])
        final_do = drift_out.decision_object
        if final_do:
            trace["final_decision_object"] = final_do.model_dump(mode="json")
        return trace
