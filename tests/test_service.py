from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def scenario(notes=None):
    return {
        "scenario_id": "TEST",
        "operator_notes": notes
        or ["Keep the battery reserve at 20 kWh from 6 PM to 9 PM."],
        "hours": [
            {
                "hour": h,
                "demand_kwh": 10,
                "solar_kwh": 0 if h < 6 or h > 17 else 20,
                "tariff_bdt_per_kwh": 5 if h < 6 else 10,
            }
            for h in range(24)
        ],
        "battery": {
            "capacity_kwh": 50,
            "initial_energy_kwh": 20,
            "minimum_energy_kwh": 0,
            "max_charge_kwh_per_hour": 20,
            "max_discharge_kwh_per_hour": 20,
        },
    }


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_reserve_directive_and_valid_schedule():
    response = client.post("/optimize-energy", json=scenario())
    assert response.status_code == 200
    body = response.json()
    assert (
        body["directive_interpretation"][0]["directive_type"]
        == "minimum_battery_reserve"
    )
    assert len(body["hourly_plan"]) == 24


def test_irrelevant_note_is_no_op():
    body = client.post(
        "/optimize-energy",
        json=scenario(["The sports office moved next month's registration deadline."]),
    ).json()
    assert body["directive_interpretation"][0]["directive_type"] == "no_op"
    assert body["directive_interpretation"][0]["applies"] is False


def test_bad_hours_are_rejected():
    payload = scenario()
    payload["hours"] = payload["hours"][:-1]
    assert client.post("/optimize-energy", json=payload).status_code == 422
