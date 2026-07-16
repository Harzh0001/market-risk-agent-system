import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="market-risk-agent")

# Add CORS middleware to allow frontend applications to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (can be restricted to specific domains later)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
