"""
Reproduz a falha de produção de 23/10/2026: o Open-Meteo respondeu
429 Too Many Requests (limite por IP, compartilhado no plano Free do Render)
e a página mostrou "Serviço meteorológico indisponível" sem nenhum dado.
"""
import pytest
import requests

from app import create_app
from app.services import forecast, geocoding, http, inmet, met_norway
from app.services.http import ServiceError

CITY = {"name": "Porto Alegre", "latitude": -30.03, "longitude": -51.23, "country": "Brasil",
        "country_code": "BR", "state": "Rio Grande do Sul", "timezone": "America/Sao_Paulo", "elevation": 10}


def _step(time, temp, rh, pressure, symbol, precip, hourly=True):
    data = {"instant": {"details": {
        "air_temperature": temp, "relative_humidity": rh, "air_pressure_at_sea_level": pressure,
        "dew_point_temperature": temp - 5, "apparent_air_temperature": temp + 1,
        "wind_speed": 4.0, "wind_from_direction": 90.0, "cloud_area_fraction": 50.0,
    }}}
    period = "next_1_hours" if hourly else "next_6_hours"
    data[period] = {"summary": {"symbol_code": symbol}, "details": {"precipitation_amount": precip}}
    return {"time": time, "data": data}


# Horários em UTC; America/Sao_Paulo é UTC-3. 02:00Z do dia 31 ainda é dia 30 no horário local.
MET_RAW = {"properties": {"timeseries": [
    _step("2026-10-30T15:00:00Z", 22.0, 60, 1014.0, "partlycloudy_day", 0.0),
    _step("2026-10-30T18:00:00Z", 26.0, 50, 1013.0, "rainandthunder", 2.5),
    _step("2026-10-31T02:00:00Z", 18.0, 90, 1012.0, "cloudy", 0.5),
    _step("2026-10-31T15:00:00Z", 24.0, 70, 1010.0, "lightrain_day", 1.0),
    _step("2026-11-01T12:00:00Z", 20.0, 80, 1018.0, "clearsky_day", 0.0, hourly=False),
]}}


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    forecast.fetch_raw.cache_clear()
    met_norway.fetch_raw.cache_clear()
    monkeypatch.setattr(forecast, "_open_meteo_paused_until", 0.0)
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    app = create_app()
    with app.test_request_context("/?lang=pt"):
        yield


def _rate_limited(*args, **kwargs):
    raise ServiceError("https://api.open-meteo.com/v1/forecast: 429 Too Many Requests", status=429)


class FakeResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status_code = status
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = "Minutely API request limit exceeded"

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error", response=self)


def test_get_json_retries_once_after_429(monkeypatch):
    responses = [FakeResponse(429, headers={"Retry-After": "1"}), FakeResponse(200, {"ok": True})]
    monkeypatch.setattr(http._session, "get", lambda *a, **k: responses.pop(0))
    assert http.get_json("https://example.test") == {"ok": True}
    assert responses == []


def test_get_json_reports_status_and_body_when_still_limited(monkeypatch):
    monkeypatch.setattr(http._session, "get", lambda *a, **k: FakeResponse(429))
    with pytest.raises(ServiceError) as exc:
        http.get_json("https://example.test")
    assert exc.value.status == 429
    assert "Minutely API request limit exceeded" in str(exc.value)


def test_weather_falls_back_to_met_norway_on_429(monkeypatch):
    monkeypatch.setattr(forecast, "fetch_raw", _rate_limited)
    monkeypatch.setattr(met_norway, "fetch_raw", lambda lat, lon: MET_RAW)

    weather = forecast.get_weather(CITY["latitude"], CITY["longitude"], CITY["timezone"])

    assert weather["source"] == "met_norway"
    assert weather["current"]["temperature"] == 22.0
    assert weather["current"]["humidity"] == 60
    days = {str(d["date"]): d for d in weather["daily"]}
    # 02:00Z de 31/10 pertence ao dia 30/10 no horário de Brasília
    assert days["2026-10-30"]["temp_min"] == 18.0
    assert days["2026-10-30"]["temp_max"] == 26.0
    assert days["2026-10-30"]["precipitation"] == 3.0
    assert days["2026-10-30"]["condition"] == "Trovoada"      # pior condição do dia
    assert days["2026-10-30"]["tornado"]["key"] == "unavailable"
    assert days["2026-10-30"]["gusts_kmh"] is None


def test_open_meteo_is_paused_after_429(monkeypatch):
    calls = []

    def limited(lat, lon):
        calls.append((lat, lon))
        _rate_limited()

    monkeypatch.setattr(forecast, "fetch_raw", limited)
    monkeypatch.setattr(met_norway, "fetch_raw", lambda lat, lon: MET_RAW)
    forecast.get_weather(-30.03, -51.23, "America/Sao_Paulo")
    forecast.get_weather(-23.55, -46.63, "America/Sao_Paulo")
    assert len(calls) == 1  # a segunda busca vai direto para a fonte reserva


def test_both_sources_down_still_raises(monkeypatch):
    monkeypatch.setattr(forecast, "fetch_raw", _rate_limited)

    def met_down(lat, lon):
        raise ServiceError("met down", status=503)

    monkeypatch.setattr(met_norway, "fetch_raw", met_down)
    with pytest.raises(ServiceError):
        forecast.get_weather(-30.03, -51.23, "America/Sao_Paulo")


def test_page_shows_data_and_notice_during_rate_limit(monkeypatch):
    monkeypatch.setattr(geocoding, "find_city", lambda q, lang="en": CITY)
    monkeypatch.setattr(forecast, "fetch_raw", _rate_limited)
    monkeypatch.setattr(met_norway, "fetch_raw", lambda lat, lon: MET_RAW)
    monkeypatch.setattr(inmet, "_active_alerts", lambda: [])

    response = create_app().test_client().get("/?city=Porto+Alegre&lang=pt")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Serviço meteorológico indisponível" not in html
    assert "22.0°C" in html
    assert "MET Norway" in html
    assert "Indisponível" in html
    assert "None" not in html
