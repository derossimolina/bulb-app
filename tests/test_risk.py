"""Modelo de risco do WYW (SPEC.md, seção 4)."""
import datetime
import json
from pathlib import Path

import pytest

from app import create_app
from app.meteo import risk
from app.meteo.sun import solar_elevation

CASES = json.loads((Path(__file__).resolve().parent.parent / "spec" / "risk-cases.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def app_ctx():
    with create_app().test_request_context("/?lang=pt"):
        yield


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: f"{c['id']:02d}-{c['name']}")
def test_shared_risk_cases(case):
    result = risk.evaluate(case["hours"], open_meteo=case.get("open_meteo", True))
    expected = case["expected"]
    assert result["level"] == expected["level"]
    assert sorted(result["indicators"]) == sorted(expected["indicators"])
    if "heat_variant" in expected:
        assert result["indicators"]["IND-CALOR"]["variant"] == expected["heat_variant"]
    assert result["tornado_info"] == expected.get("tornado_info")
    assert result["tornado_available"] == expected.get("tornado_available", True)


def test_life_risk_needs_two_indicators_in_the_same_hour():
    hours = [{"temp": 33, "tw": 31, "sun_up": True}, {"temp": 30, "tw": 27, "thunder": True}]
    result = risk.evaluate(hours)
    assert result["level"] == "attention"
    assert result["life_hours"] == []


def test_describe_lists_value_and_time():
    hours = [
        {"label": "14h", "temp": 33, "tw": 32.4, "thunder": True},
        {"label": "15h", "temp": 32, "tw": 31.2, "thunder": True, "wind_kmh": 72,
         "alerts": [{"event": "Tempestade", "severity": "Perigo"}]},
        {"label": "16h", "temp": 31, "tw": 29, "thunder": True},
    ]
    lines = risk.describe(risk.evaluate(hours), hours)
    assert "Bulbo úmido de até 32 °C entre 14h e 15h" in lines
    assert "Tempestade prevista entre 14h e 16h (aviso INMET: Perigo)" in lines
    assert "Vento de até 72 km/h às 15h" in lines


def test_heat_recommendation():
    sol = risk.evaluate([{"temp": 36, "cloud": 10, "sun_up": True}])
    assert "saia do sol" in str(risk.heat_recommendation(sol))
    sombra = risk.evaluate([{"temp": 39, "sun_up": False}])
    assert "mesmo à sombra" in str(risk.heat_recommendation(sombra))
    assert risk.heat_recommendation(risk.evaluate([{"temp": 20}])) is None


def test_solar_elevation_day_and_night():
    # Porto Alegre, 6/11: meio-dia solar ~12:30 locais (15:30 UTC); meia-noite local (03:00 UTC)
    noon = datetime.datetime(2026, 11, 6, 15, 30, tzinfo=datetime.timezone.utc)
    midnight = datetime.datetime(2026, 11, 6, 3, 0, tzinfo=datetime.timezone.utc)
    assert solar_elevation(-30.03, -51.23, noon) == pytest.approx(75, abs=2)
    assert solar_elevation(-30.03, -51.23, midnight) < -30
