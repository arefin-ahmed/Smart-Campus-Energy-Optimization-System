from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Number = Annotated[float, Field(ge=0, allow_inf_nan=False)]
DirectiveType = Literal[
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
]


class HourInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hour: int
    demand_kwh: Number
    solar_kwh: Number
    tariff_bdt_per_kwh: Number


class BatteryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capacity_kwh: Number
    initial_energy_kwh: Number
    minimum_energy_kwh: Number
    max_charge_kwh_per_hour: Number
    max_discharge_kwh_per_hour: Number

    @model_validator(mode="after")
    def validate_state(self) -> BatteryInput:
        if self.initial_energy_kwh > self.capacity_kwh:
            raise ValueError("initial energy cannot exceed capacity")
        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError("minimum energy cannot exceed capacity")
        if self.initial_energy_kwh < self.minimum_energy_kwh:
            raise ValueError("initial energy cannot be below minimum reserve")
        return self


class ScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(min_length=1)
    operator_notes: list[str] = Field(min_length=1, max_length=3)
    hours: list[HourInput]
    battery: BatteryInput

    @field_validator("operator_notes")
    @classmethod
    def notes_are_nonempty(cls, notes: list[str]) -> list[str]:
        if any(not note.strip() for note in notes):
            raise ValueError("operator notes must be non-empty")
        return notes

    @model_validator(mode="after")
    def validate_hours(self) -> ScenarioInput:
        if len(self.hours) != 24 or [item.hour for item in self.hours] != list(
            range(24)
        ):
            raise ValueError(
                "hours must contain exactly 24 entries ordered from 0 to 23"
            )
        return self


class Adjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: list[int]
    factor: float | None = None
    minimum_energy_kwh: float | None = None
    max_grid_kwh: float | None = None


class Directive(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_index: int
    applies: bool
    directive_type: DirectiveType
    structured_adjustment: Adjustment | None
    explanation: str


class HourPlan(BaseModel):
    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_action: Literal["charge", "discharge", "idle"]
    battery_kwh: float
    battery_energy_after_kwh: float


class OptimizationResponse(BaseModel):
    scenario_id: str
    directive_interpretation: list[Directive]
    hourly_plan: list[HourPlan]
    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float
    plan_summary: str
