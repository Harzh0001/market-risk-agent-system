import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


app = FastAPI(title="market-risk-agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "market-risk-agent",
        "status": "ok",
        "endpoints": ["/health", "/run", "/ui/", "/docs"],
        "ui": "/ui/",
        "openapi": "/openapi.json",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


class RunRequest(BaseModel):
    ticker: str = "^NSEI"
    run_date: str | None = None


@app.post("/run")
def run(req: RunRequest):
    from pipelines.orchestrator import MarketRiskOrchestrator

    trace = MarketRiskOrchestrator().run(run_date=req.run_date, ticker=req.ticker)
    return trace


app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend-ui")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
