"""Positive and negative test cases for market-risk-agent-system."""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_orchestrator import make_synthetic
from pipelines.orchestrator import MarketRiskOrchestrator


def _prepare_synthetic() -> tuple[str, str]:
    raw = str(ROOT / "data/raw/market_quotes.csv")
    silver = str(ROOT / "data/silver/market_clean.csv")
    make_synthetic(raw, silver, ["^NSEI", "^BSESN", "INR=X"], rows=300)
    return raw, silver


def test_positive_orchestrator_runs_and_returns_8_steps():
    _prepare_synthetic()
    trace = MarketRiskOrchestrator().run(run_date=dt.date.today().isoformat(), ticker="^NSEI")
    steps = trace.get("steps", [])
    assert len(steps) == 8, f"Expected 8 steps, got {len(steps)}"
    assert all(s.get("success") for s in steps), f"Not all steps succeeded: {steps}"
    final = trace.get("final_decision_object")
    assert final is not None, "final_decision_object missing"
    assert "var_breakdown" in final and final["var_breakdown"] is not None
    assert "compliance_flags" in final
    assert "data_lineage" in final


def test_positive_sentiment_agent_importable():
    from crews.intelligence_crew.news_sentiment_agent import NewsSentimentAgent
    assert hasattr(NewsSentimentAgent, "run")


def test_positive_sentiment_no_key_returns_neutral_fallback():
    from crews.intelligence_crew.news_sentiment_agent import NewsSentimentAgent
    agent = NewsSentimentAgent()
    out = agent.run(task="news sentiment", context={"ticker": "RELIANCE.NS"})
    assert out.success is True
    assert out.decision_object is not None
    assert out.decision_object.sentiment_label == "neutral" if hasattr(out.decision_object, "sentiment_label") else True


def test_positive_fixed_date_behavior():
    _prepare_synthetic()
    fixed = "2024-12-31"
    trace = MarketRiskOrchestrator().run(run_date=fixed, ticker="^NSEI")
    assert trace.get("run_date") == fixed


def test_negative_invalid_ticker_graceful():
    _prepare_synthetic()
    trace = MarketRiskOrchestrator().run(run_date=dt.date.today().isoformat(), ticker="INVALIDTICKER")
    steps = trace.get("steps", [])
    assert any(not s.get("success") for s in steps), "Expected at least one failure step for invalid ticker"


def test_negative_missing_clean_path_returns_early():
    trace = MarketRiskOrchestrator().run(run_date=dt.date.today().isoformat(), ticker="^NSEI")
    # Without prepare_synthetic, this should fail in normalize or var steps
    steps = trace.get("steps", [])
    assert any(s.get("agent") == "normalize" and not s.get("success") for s in steps) or \
           any(s.get("agent") == "var" and not s.get("success") for s in steps), \
           f"Expected early failure, got steps={steps}"


def test_negative_sentiment_without_news_api_key_does_not_crash():
    os.environ.pop("NEWSAPI_KEY", None)
    os.environ.pop("NEWSDATA_KEY", None)
    _prepare_synthetic()
    trace = MarketRiskOrchestrator().run(run_date=dt.date.today().isoformat(), ticker="^NSEI")
    assert "sentiment" in [s.get("agent") for s in trace.get("steps", [])]
    sentiment_step = next(s for s in trace.get("steps", []) if s.get("agent") == "sentiment")
    assert sentiment_step.get("success") is True


if __name__ == "__main__":
    cases = [
        ("TP1 orchestrator 8 steps", test_positive_orchestrator_runs_and_returns_8_steps),
        ("TP2 sentiment importable", test_positive_sentiment_agent_importable),
        ("TP3 sentiment fallback neutral", test_positive_sentiment_no_key_returns_neutral_fallback),
        ("TP4 fixed date echoed", test_positive_fixed_date_behavior),
        ("TN1 invalid ticker graceful", test_negative_invalid_ticker_graceful),
        ("TN2 missing clean path early fail", test_negative_missing_clean_path_returns_early),
        ("TN3 sentiment no key no crash", test_negative_sentiment_without_news_api_key_does_not_crash),
    ]
    results = []
    for name, fn in cases:
        try:
            fn()
            results.append((name, "PASS"))
        except AssertionError as e:
            results.append((name, f"FAIL: {e}"))
        except Exception as e:
            results.append((name, f"ERROR: {e}"))

    print("\n=== Test Results ===")
    for name, status in results:
        print(f"[{status}] {name}")
    all_pass = all(status == "PASS" for _, status in results)
    print("SUMMARY:", "PASS" if all_pass else "FAIL")
    sys.exit(0 if all_pass else 1)
