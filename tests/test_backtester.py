"""Minimal backtester agent test with graceful dependency fallback."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_fake(path: str, ticker: str = "^NSEI", rows: int = 600) -> None:
    try:
        import numpy as np  # type: ignore
        import pandas as pd  # type: ignore
    except Exception:
        sys.exit("Install numpy and pandas to run tests")
    rng = np.random.default_rng(0)
    rets = rng.normal(loc=0.0003, scale=0.012, size=rows)
    dates = pd.bdate_range(end=pd.Timestamp.today().date(), periods=rows)
    pd.DataFrame({"date": dates, "ticker": ticker, "returns": rets, "Close": 100.0}).to_csv(path, index=False)


def main() -> int:
    raw = str(ROOT / "data/raw/market_quotes.csv")
    silver = str(ROOT / "data/silver/market_clean.csv")
    Path(raw).parent.mkdir(parents=True, exist_ok=True)
    try:
        import numpy  # noqa: F401
    except Exception:
        print({"ok": False, "message": "numpy/pandas not installed", "will_run": "after pip install -e ."})
        return 0
    make_fake(raw)
    from crews.data_crew.normalize_agent import NormalizeAgent  # type: ignore
    from pipelines.backtest import BacktesterAgent  # type: ignore

    n = NormalizeAgent().run("normalize", {"raw_path": raw})
    if not n.success:
        print({"ok": False, "message": n.message})
        return 1
    b = BacktesterAgent().run("backtest", {"clean_path": silver, "ticker": "^NSEI", "backtest_window": 500})
    print({"ok": b.success, "message": b.message, "meta": b.metadata})
    return 0 if b.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
