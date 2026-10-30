import pytest
import requests

from app import create_app
from app.services import forecast, http, met_norway
from app.services.http import ServiceError

from conftest import MET_RAW


@pytest.fixture(autouse=True)
def app_ctx(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    with create_app().test_request_context("/?lang=pt"):
        yield


class FakeResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status_code = status
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = "Too Many Requests"

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


def test_get_json_reports_status_and_body(monkeypatch):
    monkeypatch.setattr(http._session, "get", lambda *a, **k: FakeResponse(429))
    with pytest.raises(ServiceError) as exc:
        http.get_json("https://example.test")
    assert exc.value.status == 429
    assert "Too Many Requests" in str(exc.value)


def test_parse_converts_utc_to_local_days():
    data = met_norway.parse(MET_RAW, "America/Sao_Paulo")
    assert data["daily"]["time"] == ["2026-10-30", "2026-10-31", "2026-11-01"]
    assert data["current"]["time"] == "2026-10-30T12:00"
    # 02:00Z de 31/10 é 23:00 de 30/10 em Brasília
    assert data["daily"]["temperature_2m_min"][0] == 18.0
    assert data["daily"]["temperature_2m_max"][0] == 26.0
    assert data["daily"]["precipitation_sum"][0] == 3.0
    assert data["daily"]["wind_speed_10m_max"][0] == 9.0


def test_symbol_to_wmo():
    assert met_norway.symbol_to_wmo("clearsky_day") == 0
    assert met_norway.symbol_to_wmo("heavyrainandthunder") == 95
    assert met_norway.symbol_to_wmo("lightrainshowers_night") == 80
    assert met_norway.symbol_to_wmo("unknownsymbol") == 3
    assert met_norway.symbol_to_wmo(None) is None


def test_get_weather_from_met_norway(monkeypatch):
    monkeypatch.setattr(met_norway, "fetch_raw", lambda lat, lon: MET_RAW)
    weather = forecast.get_weather(-30.03, -51.23, "America/Sao_Paulo")

    current = weather["current"]
    assert current["temperature"] == 22.0
    assert current["humidity"] == 60
    assert current["wind_kmh"] == 11            # 3 m/s
    assert current["pressure"]["key"] == "low"  # 1005 hPa
    assert "gusts_kmh" not in current

    day = weather["daily"][0]
    assert day["condition"] == "Trovoada"       # pior condição do dia
    assert day["wind_max_kmh"] == 32            # 9 m/s
    assert "tornado" not in day and "gusts_kmh" not in day


def test_unknown_timezone_falls_back_to_utc():
    data = met_norway.parse(MET_RAW, "Invalid/Zone")
    assert data["current"]["time"] == "2026-10-30T15:00"
