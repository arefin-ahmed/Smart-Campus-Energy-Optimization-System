from __future__ import annotations

import json
import os
import re
from typing import Any
from openai import OpenAI
from .schemas import Directive, ScenarioInput

SYSTEM_PROMPT = """Interpret each operator note into exactly one directive. Return JSON only as an array with objects containing note_index, applies, directive_type, structured_adjustment, explanation. Supported types: solar_reduction(hours,factor fraction remaining), minimum_battery_reserve(hours,minimum_energy_kwh), no_charge_window(hours), no_discharge_window(hours), max_grid_window(hours,max_grid_kwh), no_op. Use only facts present in the note; hours are 0-23 and windows are start-inclusive/end-exclusive. Irrelevant notes are no_op."""


def _hours(text: str) -> list[int]:
    found = [
        int(value)
        for value in re.findall(r"(?<!\d)([01]?\d|2[0-3])\s*(?:am|pm)?", text.lower())
    ]
    if len(found) >= 2:
        start, end = found[-2:]
        if "pm" in text.lower() and start < 12 and start not in (0,):
            start += 12
        if "pm" in text.lower() and end < 12:
            end += 12
        return list(range(start, end)) if start < end else [start]
    return sorted(set(found))


def _local_interpret(note: str, index: int) -> dict[str, Any]:
    text = note.lower()
    hours = _hours(text)
    adjustment: dict[str, Any] = {"hours": hours}
    if any(word in text for word in ("solar", "panel", "rooftop")) and any(
        word in text for word in ("reduce", "clean", "unavailable", "usable")
    ):
        percent = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        factor = (
            (100 - float(percent.group(1))) / 100
            if percent and any(word in text for word in ("reduc", "decreas"))
            else float(percent.group(1)) / 100
            if percent
            else 0.5
        )
        return {
            "note_index": index,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": hours, "factor": factor},
            "explanation": "Solar availability is reduced during the stated window.",
        }
    if "reserve" in text or "minimum battery" in text:
        amount = re.search(r"(\d+(?:\.\d+)?)\s*kwh", text)
        if amount:
            adjustment["minimum_energy_kwh"] = float(amount.group(1))
            return {
                "note_index": index,
                "applies": True,
                "directive_type": "minimum_battery_reserve",
                "structured_adjustment": adjustment,
                "explanation": "Battery energy must remain above the stated reserve.",
            }
    if "no charge" in text or "do not charge" in text:
        return {
            "note_index": index,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": adjustment,
            "explanation": "Charging is disabled during the stated window.",
        }
    if "no discharge" in text or "do not discharge" in text:
        return {
            "note_index": index,
            "applies": True,
            "directive_type": "no_discharge_window",
            "structured_adjustment": adjustment,
            "explanation": "Discharging is disabled during the stated window.",
        }
    if "grid" in text and any(
        word in text for word in ("cap", "maximum", "max", "limit")
    ):
        amount = re.search(r"(\d+(?:\.\d+)?)\s*kwh", text)
        if amount:
            adjustment["max_grid_kwh"] = float(amount.group(1))
            return {
                "note_index": index,
                "applies": True,
                "directive_type": "max_grid_window",
                "structured_adjustment": adjustment,
                "explanation": "Grid import is capped during the stated window.",
            }
    return {
        "note_index": index,
        "applies": False,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": "The note does not request a supported energy-control action.",
    }


def interpret(scenario: ScenarioInput) -> list[Directive]:
    api_key = os.getenv("OPENAI_API_KEY")
    raw: Any = None
    if api_key:
        client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or None)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps({"operator_notes": scenario.operator_notes}),
                },
            ],
            timeout=8,
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        raw = raw.get("directives", raw) if isinstance(raw, dict) else raw
    if not isinstance(raw, list) or len(raw) != len(scenario.operator_notes):
        raw = [
            _local_interpret(note, index)
            for index, note in enumerate(scenario.operator_notes)
        ]
    return [Directive.model_validate(item) for item in raw]
