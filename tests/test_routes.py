import pytest

from app import create_app
from app.services import geocoding, inmet, met_norway

from conftest import MET_RAW

CITY = {"name": "Porto Alegre", "latitude": -30.03, "longitude": -51.23, "country": "Brasil",
        "country_code": "BR", "state": "Rio Grande do Sul", "timezone": "America/Sao_Paulo", "elevation": 10}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(geocoding, "find_city", lambda q, lang="en": CITY)
    monkeypatch.setattr(met_norway, "fetch_raw", lambda lat, lon: MET_RAW)
    monkeypatch.setattr(inmet, "_active_alerts", lambda: [("today", {
        "id_aviso": 1, "descricao": "Tempestade", "severidade": "Grande Perigo", "aviso_cor": "#C80000",
        "inicio": "2026-10-15 00:00", "fim": "2026-10-15 23:59", "geocodes": "4314902",
        "riscos": ["Risco"], "instrucoes": ["Instrução"]})])
    return create_app().test_client()


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Wet Bulb Temperature Calculator" in response.data


def test_city_forecast_with_alerts(client):
    html = client.get("/?city=Porto+Alegre&lang=pt").get_data(as_text=True)
    assert "Previsão do tempo para 7 dias" in html
    assert "Tempestade" in html and "Grande Perigo" in html
    assert "Baixa pressão" in html          # 1005 hPa
    assert "Trovoada" in html               # pior condição do dia 30
    for removed in ("Tornado", "Rajadas", "None"):
        assert removed not in html


def test_post_redirects_to_get(client):
    response = client.post("/", data={"city": "Porto Alegre"})
    assert response.status_code == 302 and "city=Porto" in response.location


def test_city_not_found(client, monkeypatch):
    def not_found(q, lang="en"):
        raise geocoding.CityNotFound(q)
    monkeypatch.setattr(geocoding, "find_city", not_found)
    assert b"City not found" in client.get("/?city=Xyzzy").data


def test_parse_query():
    assert geocoding.parse_query("Paris, FR") == ("Paris", "FR")
    assert geocoding.parse_query("Porto Alegre") == ("Porto Alegre", None)


@pytest.mark.parametrize("region,result,expected", [
    ("RS", {"country_code": "BR", "admin1": "Rio Grande do Sul"}, True),
    ("RS", {"country_code": "BR", "admin1": "Santa Catarina"}, False),
    ("RS", {"country_code": "RS", "admin1": "Belgrade"}, True),
    ("Oklahoma", {"country_code": "US", "admin1": "Oklahoma"}, True),
    ("Oklahoma", {"country_code": "US", "admin1": "Texas"}, False),
    ("brasil", {"country_code": "BR", "country": "Brasil"}, True),
])
def test_matches_region(region, result, expected):
    assert geocoding._matches_region(result, region) is expected
