from __future__ import annotations

import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from .guardrails import validate_directives
from .interpreter import interpret
from .optimizer import optimize
from .schemas import OptimizationResponse, ScenarioInput
from .verifier import verify

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="GridWise Energy Optimization API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def internal_error(_, exc: Exception):
    logging.exception("controlled request failure: %s", exc)
    return JSONResponse(
        status_code=500, content={"detail": "internal optimization error"}
    )


@app.post("/optimize-energy", response_model=OptimizationResponse)
def optimize_energy(scenario: ScenarioInput) -> OptimizationResponse:
    try:
        directives = validate_directives(interpret(scenario), scenario)
        plans = optimize(scenario, directives)
        total_grid, total_cost, peak_grid = verify(scenario, directives, plans)
        return OptimizationResponse(
            scenario_id=scenario.scenario_id,
            directive_interpretation=directives,
            hourly_plan=plans,
            total_grid_kwh=total_grid,
            total_cost_bdt=total_cost,
            peak_grid_kwh=peak_grid,
            plan_summary=f"Optimized 24-hour schedule with {len(directives)} operator note interpretations.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
