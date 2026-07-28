"""News sentiment agent for market risk decisions."""
from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import requests

from crews.base_agent import Agent, AgentResult, register
from schemas.decision_objects import DataSource, Lineage, RiskDecisionObject

LOGGER = logging.getLogger("market-risk.news")

_POSITIVE = {
    "up", "gain", "gains", "grew", "grow", "growth", "rose", "rising", "surge", "surges",
    "strong", "bullish", "beat", "beats", "outperform", "positive", "rally", "rallies",
    "profit", "profits", "record", "boost", "boosts", "beat", "beats", "expansion",
    "accelerate", "accelerates", "upgrade", "upgrades", "recovery", "recoveries",
    "dividend", "dividends", "buyback", "buybacks", "demand", "demands", "hiring",
    "hires", "merger", "acquisition", "beats", "exceeded", "exceeds", "raised",
    "raises", "stronger", "strengthen", "strengthens", "optimistic", "bullish",
}
_NEGATIVE = {
    "down", "loss", "losses", "fell", "fall", "falling", "plunge", "plunges", "drop",
    "drops", "weak", "bearish", "miss", "misses", "underperform", "negative", "selloff",
    "sell-off", "outflow", "outflows", "cut", "cuts", "downgrade", "downgrades",
    "recession", "layoff", "layoffs", "concern", "concerns", "risk", "risks", "crisis",
    "debt", "deficit", "inflation", "recession", "slowdown", "slow", "slower",
    "slowest", "weakest", "warning", "warn", "warns", "investigation", "probe",
    "regulatory", "sanction", "sanctions", "tariff", "tariffs", "restructuring",
    "fraud", "lawsuit", "litigation", "missed", "misses", "lowered", "lowers",
    "weaker", "weakening", "pessimistic", "bearish",
}


def _fetch_news(query: str, limit: int = 25) -> list[str]:
    api_key = os.getenv("NEWSAPI_KEY") or os.getenv("NEWSDATA_KEY")
    if not api_key:
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": limit,
        "apiKey": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        articles = data.get("articles", [])
        texts = []
        for a in articles:
            title = a.get("title") or ""
            desc = a.get("description") or ""
            if title:
                texts.append(title)
            if desc:
                texts.append(desc)
        return texts
    except Exception as exc:
        LOGGER.warning("News fetch failed: %s", exc)
        return []


def _score_texts(texts: list[str]) -> Dict[str, Optional[float]]:
    if not texts:
        return {"sentiment_score": 0.0, "sentiment_label": "neutral", "articles": 0}

    pos = 0
    neg = 0
    total = 0
    for t in texts:
        low = t.lower()
        words = {w.strip(".,!?:;-\"'()[]{}") for w in low.split()}
        pk = len(words & _POSITIVE)
        nk = len(words & _NEGATIVE)
        pos += pk
        neg += nk
        total += 1

    score = 0.0
    denom = max(pos + neg, 1)
    score = (pos - neg) / denom
    if score > 0.25:
        label = "positive"
    elif score < -0.25:
        label = "negative"
    else:
        label = "neutral"

    return {"sentiment_score": score, "sentiment_label": label, "articles": total}


@register
class NewsSentimentAgent(Agent):
    name = "news-sentiment-agent"
    role = "intelligence"

    def run(self, task: str, context: Dict[str, Any]) -> AgentResult:
        ticker = context.get("ticker", "^NSEI")
        symbol = ticker.replace("^", "")
        texts = _fetch_news(symbol, limit=25)
        score_data = _score_texts(texts)

        lineage = Lineage(
            source=DataSource.NEWS,
            dataset="news_sentiment_v1",
            version="v1",
            as_of=dt.datetime.utcnow(),
            quality_score=min(score_data["articles"] / 25.0, 1.0),
        )

        decision = RiskDecisionObject(
            decision_id=f"sentiment-{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            risk_bucket="market",
            instrument_or_exposure_id=ticker,
            as_of_date=dt.datetime.utcnow(),
            model_version="sentiment-v1",
            model_technique="news-keyword",
            confidence=float(np.clip(abs(score_data["sentiment_score"]) + 0.1, 0.0, 0.99)),
            data_lineage=[lineage],
            explanation=(
                f"news sentiment={score_data['sentiment_label']} "
                f"(score={score_data['sentiment_score']:.3f}, "
                f"articles={score_data['articles']})"
            ),
        )
        return AgentResult(
            success=True,
            message=f"Fetched {score_data['articles']} articles; sentiment={score_data['sentiment_label']}",
            decision_object=decision,
        )
