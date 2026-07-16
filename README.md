# Market Risk Agent System

Multi-agent RBI-aligned market risk prediction system.

## Run
```bash
python -m tests.test_orchestrator
python -m tests.test_backtester
```

## Kimi LLM mode
Set in `infra/config.yaml`:
```yaml
llm:
  enabled: true
```
Then set `MOONSHOT_API_KEY` in `.env`. Kimi calls are optional; without the key the system falls back to heuristic rules.

## Deploy
Push to GitHub, connect Railway. Uses:
`python -m uvicorn frontend.main:app --host 0.0.0.0 --port $PORT`

## Architecture
See `README_FULL.txt`.
