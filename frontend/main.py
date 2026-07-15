from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="market-risk-agent")


class RunRequest(BaseModel):
    ticker: str = "^NSEI"
    run_date: str | None = None


@app.get("/")
def root():
    return {
        "service": "market-risk-agent",
        "status": "ok",
        "endpoints": ["/health", "/run"],
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run(req: RunRequest):
    from pipelines.orchestrator import MarketRiskOrchestrator

    trace = MarketRiskOrchestrator().run(run_date=req.run_date, ticker=req.ticker)
    return trace


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
