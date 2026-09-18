from __future__ import annotations

import math
from .schemas import Directive, HourPlan, ScenarioInput

TOLERANCE = 1e-4


def verify(
    scenario: ScenarioInput, directives: list[Directive], plans: list[HourPlan]
) -> tuple[float, float, float]:
    if len(plans) != 24 or [item.hour for item in plans] != list(range(24)):
        raise ValueError("invalid hourly plan")
    battery = scenario.battery
    solar_factors = [1.0] * 24
    reserves = [battery.minimum_energy_kwh] * 24
    no_charge, no_discharge = set(), set()
    caps = [math.inf] * 24
    for directive in directives:
        if not directive.applies or directive.structured_adjustment is None:
            continue
        adjustment = directive.structured_adjustment
        for h in adjustment.hours:
            if directive.directive_type == "solar_reduction":
                solar_factors[h] *= adjustment.factor or 0
            elif directive.directive_type == "minimum_battery_reserve":
                reserves[h] = max(reserves[h], adjustment.minimum_energy_kwh or 0)
            elif directive.directive_type == "no_charge_window":
                no_charge.add(h)
            elif directive.directive_type == "no_discharge_window":
                no_discharge.add(h)
            elif directive.directive_type == "max_grid_window":
                caps[h] = min(caps[h], adjustment.max_grid_kwh or 0)
    for h, plan in enumerate(plans):
        values = (
            plan.grid_kwh,
            plan.solar_used_kwh,
            plan.battery_kwh,
            plan.battery_energy_after_kwh,
        )
        if any(not math.isfinite(value) or value < -TOLERANCE for value in values):
            raise ValueError("negative or non-finite schedule value")
        charge = plan.battery_kwh if plan.battery_action == "charge" else 0
        discharge = plan.battery_kwh if plan.battery_action == "discharge" else 0
        if (
            abs(
                plan.grid_kwh
                + plan.solar_used_kwh
                + discharge
                - scenario.hours[h].demand_kwh
                - charge
            )
            > TOLERANCE
        ):
            raise ValueError("energy balance violation")
        if (
            plan.solar_used_kwh
            > scenario.hours[h].solar_kwh * solar_factors[h] + TOLERANCE
        ):
            raise ValueError("solar limit violation")
        previous = (
            battery.initial_energy_kwh
            if h == 0
            else plans[h - 1].battery_energy_after_kwh
        )
        if (
            abs(plan.battery_energy_after_kwh - previous - charge + discharge)
            > TOLERANCE
        ):
            raise ValueError("battery transition violation")
        if (
            plan.battery_energy_after_kwh < reserves[h] - TOLERANCE
            or plan.battery_energy_after_kwh > battery.capacity_kwh + TOLERANCE
        ):
            raise ValueError("battery reserve or capacity violation")
        if (
            charge > battery.max_charge_kwh_per_hour + TOLERANCE
            or discharge > battery.max_discharge_kwh_per_hour + TOLERANCE
        ):
            raise ValueError("battery rate violation")
        if (
            h in no_charge
            and charge > TOLERANCE
            or h in no_discharge
            and discharge > TOLERANCE
            or plan.grid_kwh > caps[h] + TOLERANCE
        ):
            raise ValueError("directive violation")
    if abs(plans[-1].battery_energy_after_kwh - battery.initial_energy_kwh) > TOLERANCE:
        raise ValueError("battery neutrality violation")
    total_grid = sum(plan.grid_kwh for plan in plans)
    total_cost = sum(
        plan.grid_kwh * item.tariff_bdt_per_kwh
        for plan, item in zip(plans, scenario.hours)
    )
    return total_grid, total_cost, max(plan.grid_kwh for plan in plans)
