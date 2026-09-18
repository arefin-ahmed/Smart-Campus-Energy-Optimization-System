from __future__ import annotations

from ortools.linear_solver import pywraplp
from .schemas import Directive, ScenarioInput, HourPlan


def optimize(scenario: ScenarioInput, directives: list[Directive]) -> list[HourPlan]:
    solver = pywraplp.Solver.CreateSolver("CBC")
    if solver is None:
        raise RuntimeError("optimizer unavailable")
    battery = scenario.battery
    solar_factors = [1.0] * 24
    reserves = [battery.minimum_energy_kwh] * 24
    no_charge: set[int] = set()
    no_discharge: set[int] = set()
    grid_caps = [solver.infinity()] * 24
    for directive in directives:
        if not directive.applies or directive.structured_adjustment is None:
            continue
        adjustment = directive.structured_adjustment
        for hour in adjustment.hours:
            if directive.directive_type == "solar_reduction":
                solar_factors[hour] *= adjustment.factor or 0.0
            elif directive.directive_type == "minimum_battery_reserve":
                reserves[hour] = max(
                    reserves[hour], adjustment.minimum_energy_kwh or 0.0
                )
            elif directive.directive_type == "no_charge_window":
                no_charge.add(hour)
            elif directive.directive_type == "no_discharge_window":
                no_discharge.add(hour)
            elif directive.directive_type == "max_grid_window":
                grid_caps[hour] = min(grid_caps[hour], adjustment.max_grid_kwh or 0.0)

    grid = [solver.NumVar(0, grid_caps[h], f"grid_{h}") for h in range(24)]
    solar = [
        solver.NumVar(0, scenario.hours[h].solar_kwh * solar_factors[h], f"solar_{h}")
        for h in range(24)
    ]
    charge = [
        solver.NumVar(
            0, 0 if h in no_charge else battery.max_charge_kwh_per_hour, f"charge_{h}"
        )
        for h in range(24)
    ]
    discharge = [
        solver.NumVar(
            0,
            0 if h in no_discharge else battery.max_discharge_kwh_per_hour,
            f"discharge_{h}",
        )
        for h in range(24)
    ]
    charging = [solver.BoolVar(f"charging_{h}") for h in range(24)]
    for h in range(24):
        solver.Add(charge[h] <= battery.max_charge_kwh_per_hour * charging[h])
        solver.Add(
            discharge[h] <= battery.max_discharge_kwh_per_hour * (1 - charging[h])
        )
    energy = [
        solver.NumVar(reserves[h], battery.capacity_kwh, f"energy_{h}")
        for h in range(24)
    ]
    for h, item in enumerate(scenario.hours):
        solver.Add(grid[h] + solar[h] + discharge[h] == item.demand_kwh + charge[h])
        previous = battery.initial_energy_kwh if h == 0 else energy[h - 1]
        solver.Add(energy[h] == previous + charge[h] - discharge[h])
    solver.Add(energy[23] == battery.initial_energy_kwh)
    solver.Minimize(
        sum(grid[h] * scenario.hours[h].tariff_bdt_per_kwh for h in range(24))
    )
    if solver.Solve() != pywraplp.Solver.OPTIMAL:
        raise ValueError("scenario and directives have no feasible schedule")
    plans: list[HourPlan] = []
    for h in range(24):
        charge_value, discharge_value = (
            charge[h].solution_value(),
            discharge[h].solution_value(),
        )
        flow = charge_value if charge_value > 1e-7 else discharge_value
        action = (
            "charge"
            if charge_value > 1e-7
            else "discharge"
            if discharge_value > 1e-7
            else "idle"
        )
        plans.append(
            HourPlan(
                hour=h,
                grid_kwh=grid[h].solution_value(),
                solar_used_kwh=solar[h].solution_value(),
                battery_action=action,
                battery_kwh=flow,
                battery_energy_after_kwh=energy[h].solution_value(),
            )
        )
    return plans
