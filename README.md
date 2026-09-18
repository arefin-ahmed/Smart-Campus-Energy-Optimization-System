# GridWise Energy Optimization API

Python implementation for the BUP CSE Fest 2026 Smart Campus Energy Optimization challenge.

## Stack

- FastAPI and Pydantic for the HTTP API and strict schemas
- OR-Tools GLOP linear programming solver for cost minimization
- OpenAI-compatible structured-output model for operator-note interpretation
- Conservative local parser as a no-secret Docker fallback; its result is still passed through the same deterministic guardrails

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY = "..." # optional for the hosted LLM path
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Environment variables: `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`), `OPENAI_BASE_URL` (optional OpenAI-compatible endpoint), and `PORT` (default `8080`). No secret is baked into the image.

## Docker

```powershell
docker build -t gridwise-api .
docker run --rm -p 8080:8080 -e OPENAI_API_KEY=$env:OPENAI_API_KEY gridwise-api
```

## API

```powershell
curl http://localhost:8080/health
curl -X POST http://localhost:8080/optimize-energy `
  -H "Content-Type: application/json" `
  --data-binary '@request.json'
```

The POST body must contain 24 ordered hours, one to three operator notes, and the battery object described in the challenge statement. The response contains one guarded directive interpretation per note, a validated 24-hour plan, total grid energy, total cost, peak grid import, and a summary.

## Tests

```powershell
pytest -q
```

The public cases can be replayed by extracting each `cases[*].input` object from `BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json` and POSTing it to `/optimize-energy`. Public note text and schedules are never used as fixtures in the implementation.
