import pytest

from app import create_app
from app.meteo.indices import classify_pressure
from app.meteo.wetbulb import calculate_wet_bulb


@pytest.fixture(autouse=True)
def app_ctx():
    # lazy_gettext precisa de contexto Flask para resolver traduções
    app = create_app()
    with app.test_request_context():
        yield


def test_wet_bulb_stull_reference():
    # Valor de referência de Stull (2011): T=20 °C, UR=50% → Tw ≈ 13,7 °C
    assert calculate_wet_bulb(20, 50) == pytest.approx(13.7, abs=0.1)


def test_wet_bulb_none():
    assert calculate_wet_bulb(None, 50) is None


def test_pressure_classification_and_trend():
    assert classify_pressure(1025)["key"] == "high"
    assert classify_pressure(1000)["key"] == "low"
    assert classify_pressure(1013)["key"] == "normal"
    assert classify_pressure(1013, 1018)["trend"]["key"] == "falling"
    assert classify_pressure(1013, 1009)["trend"]["key"] == "rising"
    assert classify_pressure(1013, 1012)["trend"]["key"] == "steady"
    assert classify_pressure(None) is None

