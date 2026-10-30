import pytest

from app.services import met_norway


def met_step(time, temp, rh, pressure, symbol, precip, wind=4.0, hourly=True):
    """Um passo da série do MET Norway (locationforecast/2.0/complete)."""
    data = {"instant": {"details": {
        "air_temperature": temp, "relative_humidity": rh, "air_pressure_at_sea_level": pressure,
        "dew_point_temperature": temp - 5, "apparent_air_temperature": temp + 1,
        "wind_speed": wind, "wind_from_direction": 90.0, "cloud_area_fraction": 50.0,
    }}}
    period = "next_1_hours" if hourly else "next_6_hours"
    data[period] = {"summary": {"symbol_code": symbol}, "details": {"precipitation_amount": precip}}
    return {"time": time, "data": data}


# Horários em UTC; America/Sao_Paulo é UTC-3. 02:00Z do dia 31 ainda é dia 30 no horário local.
MET_RAW = {"properties": {"timeseries": [
    met_step("2026-10-30T15:00:00Z", 22.0, 60, 1005.0, "partlycloudy_day", 0.0, wind=3.0),
    met_step("2026-10-30T18:00:00Z", 26.0, 50, 1004.0, "rainandthunder", 2.5, wind=9.0),
    met_step("2026-10-31T02:00:00Z", 18.0, 90, 1006.0, "cloudy", 0.5),
    met_step("2026-10-31T15:00:00Z", 24.0, 70, 1010.0, "lightrain_day", 1.0),
    met_step("2026-11-01T12:00:00Z", 20.0, 80, 1018.0, "clearsky_day", 0.0, hourly=False),
]}}


@pytest.fixture(autouse=True)
def clear_caches():
    met_norway.fetch_raw.cache_clear()
    yield
