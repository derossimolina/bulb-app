import pytest

from app import create_app
from app.meteo.indices import bulk_shear, classify_pressure, tornado_potential_day, tornado_potential_hour
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


def test_bulk_shear():
    # 10 m/s de oeste (270°) em baixo, 30 m/s de oeste em cima → 20 m/s
    assert bulk_shear(10, 270, 30, 270) == pytest.approx(20)
    # mesma velocidade, direções opostas → 2× velocidade
    assert bulk_shear(10, 0, 10, 180) == pytest.approx(20)
    assert bulk_shear(None, 0, 10, 180) is None


@pytest.mark.parametrize("cape,li,deep,low,expected", [
    (50, 0, 30, 15, "very_low"),      # sem instabilidade
    (500, -2, 10, 5, "very_low"),     # WMAXSHEAR ≈ 316 < 400
    (800, -2, 18, 5, "low"),          # WMAXSHEAR ≈ 720
    (1500, -3, 20, 10, "moderate"),   # WMAXSHEAR ≈ 1095
    (3000, -6, 25, 15, "high"),       # WMAXSHEAR ≈ 1936
])
def test_tornado_levels(cape, li, deep, low, expected):
    level, _ = tornado_potential_hour(cape, li, deep, low)
    assert level == expected


def test_tornado_day_takes_worst_hour():
    hours = [
        {"cape": 0, "lifted_index": 2, "deep_shear": 5, "low_shear": 2},
        {"cape": 3000, "lifted_index": -6, "deep_shear": 25, "low_shear": 15},
    ]
    assert tornado_potential_day(hours)["key"] == "high"


def test_tornado_unavailable_without_cape():
    assert tornado_potential_day([])["key"] == "unavailable"
    assert tornado_potential_day([{"cape": None, "deep_shear": None}])["key"] == "unavailable"
