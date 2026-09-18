from __future__ import annotations

import math
from pydantic import ValidationError
from .schemas import Directive, ScenarioInput

SUPPORTED = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}


def validate_directives(
    directives: list[Directive], scenario: ScenarioInput
) -> list[Directive]:
    if len(directives) != len(scenario.operator_notes) or [
        d.note_index for d in directives
    ] != list(range(len(directives))):
        raise ValueError("one ordered interpretation is required for every note")
    capacity = scenario.battery.capacity_kwh
    validated: list[Directive] = []
    for directive in directives:
        adjustment = directive.structured_adjustment
        if directive.directive_type not in SUPPORTED:
            raise ValueError("unsupported directive")
        if directive.directive_type == "no_op":
            if directive.applies or adjustment is not None:
                raise ValueError("no_op must not apply")
            validated.append(directive)
            continue
        if not directive.applies or adjustment is None:
            raise ValueError("active directives require an adjustment")
        hours = adjustment.hours
        if hours != sorted(set(hours)) or any(
            not isinstance(hour, int) or hour < 0 or hour > 23 for hour in hours
        ):
            raise ValueError(
                "directive hours must be unique, ascending integers in 0..23"
            )
        if directive.directive_type == "solar_reduction":
            if (
                adjustment.factor is None
                or not math.isfinite(adjustment.factor)
                or not 0 <= adjustment.factor <= 1
            ):
                raise ValueError("solar factor must be between 0 and 1")
        elif directive.directive_type == "minimum_battery_reserve":
            if (
                adjustment.minimum_energy_kwh is None
                or not math.isfinite(adjustment.minimum_energy_kwh)
                or not 0 <= adjustment.minimum_energy_kwh <= capacity
            ):
                raise ValueError("invalid battery reserve")
        elif directive.directive_type == "max_grid_window":
            if (
                adjustment.max_grid_kwh is None
                or not math.isfinite(adjustment.max_grid_kwh)
                or adjustment.max_grid_kwh < 0
            ):
                raise ValueError("invalid grid cap")
        elif (
            adjustment.factor is not None
            or adjustment.minimum_energy_kwh is not None
            or adjustment.max_grid_kwh is not None
        ):
            raise ValueError("window directives cannot contain numeric fields")
        validated.append(directive)
    return validated
