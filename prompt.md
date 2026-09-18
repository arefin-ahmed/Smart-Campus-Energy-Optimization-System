Build a production-ready solution for the BUP CSE Fest 2026
Smart Campus Energy Optimization Challenge:
LLM-Assisted Operator Directive Interpretation.

OBJECTIVE

Create one public HTTP API service that receives a synthetic
24-hour campus energy scenario and 1-3 natural-language operator
notes.

The system must:

1. Interpret every operator note using a language-capable generative model.
2. Convert each note into exactly one supported structured directive.
3. Correctly classify irrelevant notes as no_op.
4. Validate all LLM output using deterministic guardrails.
5. Apply every valid directive to the optimization model.
6. Generate a valid 24-hour energy schedule.
7. Minimize total grid electricity cost.
8. Return the exact required JSON response schema.

IMPORTANT:
The LLM must be part of the actual operator-note interpretation path.
Do not use the LLM only for explanation or plan_summary.
Do not use hard-coded phrase matching as the sole interpreter.

SUPPORTED DIRECTIVES

solar_reduction:
{
  "hours": [...],
  "factor": number
}

minimum_battery_reserve:
{
  "hours": [...],
  "minimum_energy_kwh": number
}

no_charge_window:
{
  "hours": [...]
}

no_discharge_window:
{
  "hours": [...]
}

max_grid_window:
{
  "hours": [...],
  "max_grid_kwh": number
}

no_op:
{
  "applies": false,
  "structured_adjustment": null
}

INTERPRETATION RULES

- Exactly one interpretation per operator note.
- Preserve note_index.
- Return note_index values in order.
- Non-no_op directives must use applies=true.
- no_op must use applies=false.
- Hours must be unique integers 0-23 in ascending order.
- Time windows are start-inclusive and end-exclusive.
- solar_reduction factor represents the fraction remaining.
- factor must be between 0 and 1.
- Battery reserve must be non-negative and cannot exceed battery capacity.
- max_grid_kwh must be finite and non-negative.
- Never invent unsupported directives or scenario values.
- Handle paraphrased natural language.
- Handle equivalent time and percentage expressions.

API

GET /health

Return HTTP 200:

{
  "status": "ok"
}

POST /optimize-energy

Accept the exact scenario schema:

{
  "scenario_id": "string",
  "operator_notes": ["string"],
  "hours": [
    {
      "hour": 0,
      "demand_kwh": number,
      "solar_kwh": number,
      "tariff_bdt_per_kwh": number
    }
  ],
  "battery": {
    "capacity_kwh": number,
    "initial_energy_kwh": number,
    "minimum_energy_kwh": number,
    "max_charge_kwh_per_hour": number,
    "max_discharge_kwh_per_hour": number
  }
}

There must be exactly 24 hourly entries covering 0-23.

OPTIMIZATION

Minimize:

SUM(grid_kwh[h] * tariff_bdt_per_kwh[h])

Subject to:

grid_kwh >= 0

solar_used_kwh >= 0

solar_used_kwh <= effective_solar_kwh

battery_energy_after >= minimum_energy

battery_energy_after <= capacity

charge <= max_charge_kwh_per_hour

discharge <= max_discharge_kwh_per_hour

grid + solar_used + battery_discharge
=
demand + battery_charge

final battery energy = initial battery energy

DIRECTIVE APPLICATION

solar_reduction:
effective_solar[h] = original_solar[h] * factor

minimum_battery_reserve:
battery_energy_after[h] >= specified reserve

no_charge_window:
battery charge = 0 during specified hours

no_discharge_window:
battery discharge = 0 during specified hours

max_grid_window:
grid_kwh[h] <= specified maximum

no_op:
no optimization constraint is added.

ARCHITECTURE

Implement:

API Layer
→ LLM Interpreter
→ Structured Output Parser
→ Deterministic Guardrail Validator
→ Directive Normalizer
→ Optimization Model
→ Schedule Validator
→ Response Builder

Do not allow invalid LLM output to reach the optimizer.

FINAL VALIDATION

Before returning the response, independently verify:

- 24 unique hours
- correct hour ordering
- non-negative values
- energy balance for every hour
- effective solar limit
- battery state transitions
- battery capacity
- minimum reserve
- charge rate
- discharge rate
- all operator directives
- final battery neutrality
- total_grid_kwh
- total_cost_bdt
- peak_grid_kwh

The final response must contain:

{
  "scenario_id": "string",
  "directive_interpretation": [...],
  "hourly_plan": [...],
  "total_grid_kwh": number,
  "total_cost_bdt": number,
  "peak_grid_kwh": number,
  "plan_summary": "string"
}

ERROR HANDLING

400 for malformed or structurally invalid JSON.

422 may be used for semantically invalid input.

500 for controlled internal errors.

Never expose:
- API keys
- tokens
- passwords
- environment secrets
- raw stack traces

PERFORMANCE

POST /optimize-energy must complete within 30 seconds.
Target p95 latency <= 5 seconds.

Use efficient LLM calls.
Prefer structured JSON output.
Use deterministic preprocessing/postprocessing where appropriate.
Consider caching carefully if it does not compromise correctness.

RELIABILITY

Handle:
- malformed LLM output
- unsupported directive types
- missing fields
- invalid hours
- invalid numeric values
- LLM provider errors
- repeated requests
- unexpected but valid numeric scenarios

Do not crash the service.

DEPLOYMENT

The service must:
- be externally reachable
- require no login for judging
- expose /health
- expose /optimize-energy
- bind to 0.0.0.0
- have no secrets baked into Docker
- include a Docker fallback
- include a self-contained README
- include environment variable names
- document the LLM provider/model
- document the optimizer/solver
- include curl examples
- include public sample testing instructions

IMPLEMENTATION QUALITY

Use clean modular architecture.
Separate:
- API
- LLM interpretation
- schemas
- validation
- directive processing
- optimization
- final verification

Write unit tests for each directive type and paraphrased operator-note examples.

Do not hard-code the public sample phrases.

The hidden tests will use paraphrased language,
different energy values, different tariffs,
different battery conditions, and combinations
of supported directives.

Build the solution for generalization rather than
matching known examples.