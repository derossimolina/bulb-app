"""Janela de risco montada a partir do MET Norway e do INMET (SPEC.md 4.1 e REQ-WEB-40 a 43)."""
import datetime

import pytest

from app import create_app
from app.services import geocoding, inmet, met_norway, risk_window

UTC = datetime.timezone.utc
# Porto Alegre (UTC-3). 15:00Z = 12h locais, com sol.
HOURLY = {
    "time_utc": [f"2026-11-06T{h:02d}:00:00+00:00" for h in (14, 15, 16, 17, 18, 21)],
    "time": [f"2026-11-06T{h - 3:02d}:00" for h in (14, 15, 16, 17, 18, 21)],
    "temperature_2m": [30, 36, 34, 33, 31, 25],
    "relative_humidity_2m": [40, 30, 85, 85, 60, 70],
    "cloud_cover": [10, 20, 90, 90, 90, 90],
    "weather_code": [1, 1, 95, 3, 3, 95],
    "wind_speed_10m": [5, 5, 10, 18, 5, 5],
}
NOW = datetime.datetime(2026, 11, 6, 15, 20, tzinfo=UTC)
CITY = {"name": "Porto Alegre", "latitude": -30.03, "longitude": -51.23, "country": "Brasil",
        "country_code": "BR", "state": "Rio Grande do Sul", "timezone": "America/Sao_Paulo"}


@pytest.fixture(autouse=True)
def app_ctx():
    with create_app().test_request_context("/?lang=pt"):
        yield


def test_window_starts_at_current_hour_and_stops_at_gaps():
    hours = risk_window.build_hours(HOURLY, CITY["latitude"], CITY["longitude"], now=NOW)
    assert [h["label"] for h in hours] == ["12h", "13h", "14h", "15h"]   # 14Z já passou; 21Z fica fora
    assert hours[0]["sun_up"] and hours[0]["temp"] == 36
    assert hours[1]["thunder"] and not hours[0]["thunder"]
    assert hours[2]["wind_kmh"] == pytest.approx(64.8)   # 18 m/s às 14h


def test_alerts_apply_only_inside_their_period():
    alerts = [{"event": "Tempestade", "severity": "Perigo", "start": "2026-11-06 13:30", "end": "2026-11-06 14:10"}]
    hours = risk_window.build_hours(HOURLY, CITY["latitude"], CITY["longitude"], alerts, now=NOW)
    assert [bool(h["alerts"]) for h in hours] == [False, True, True, False]


def test_assess_combines_indicators_in_the_same_hour():
    result = risk_window.assess({"hourly": HOURLY}, CITY["latitude"], CITY["longitude"], now=NOW)
    # 13h: trovoada + bulbo úmido de 34 °C a 85 % (≈ 31,8 °C) → Risco à sua vida
    assert result["level"] == "life"
    assert result["life_hours"] == [1]
    assert "Tempestade prevista às 13h" in result["lines"]
    assert str(result["recommendation"]).startswith("Se estiver ao ar livre e ao sol")
    assert result["tornado_available"] is False


def _client(monkeypatch, alerts=()):
    raw = {"properties": {"timeseries": [
        {"time": stamp.replace("+00:00", "Z"), "data": {
            "instant": {"details": {"air_temperature": t, "relative_humidity": rh, "cloud_area_fraction": c,
                                    "wind_speed": w, "air_pressure_at_sea_level": 1010.0}},
            "next_1_hours": {"summary": {"symbol_code": "rainandthunder" if code == 95 else "cloudy"},
                             "details": {"precipitation_amount": 1.0}}}}
        for stamp, t, rh, c, w, code in zip(HOURLY["time_utc"], HOURLY["temperature_2m"],
                                            HOURLY["relative_humidity_2m"], HOURLY["cloud_cover"],
                                            HOURLY["wind_speed_10m"], HOURLY["weather_code"])]}}
    monkeypatch.setattr(geocoding, "find_city", lambda q, lang="en": CITY)
    monkeypatch.setattr(met_norway, "fetch_raw", lambda lat, lon: raw)
    monkeypatch.setattr(inmet, "_active_alerts", lambda: list(alerts))
    monkeypatch.setattr(risk_window, "_now", lambda: NOW)
    return create_app().test_client()


def test_page_shows_red_life_risk_banner(monkeypatch):
    html = _client(monkeypatch).get("/?city=Porto+Alegre&lang=pt").get_data(as_text=True)
    banner = html[html.index("risk-banner"):html.index('class="current-grid"')]
    assert "risk-banner-life" in banner
    assert "Risco à sua vida!" in banner and "fa-exclamation-triangle" in banner
    assert "Tempestade prevista às 13h" in banner
    assert "Este indicador não substitui os alertas das autoridades e da Defesa Civil." in banner
    assert "Indicador de tornado indisponível no momento." in banner
    assert html.index("risk-banner") < html.index('class="current-grid"')   # acima dos cards


def test_page_header_and_footer(monkeypatch):
    html = _client(monkeypatch).get("/?lang=pt").get_data(as_text=True)
    assert "<title>WYW</title>" in html and "<h1>WYW</h1>" in html
    assert '<a href="https://derossi.dev">derossi research</a>' in html
