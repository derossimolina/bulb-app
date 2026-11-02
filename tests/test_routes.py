import pytest

from app import create_app
from app.services import geocoding, inmet, met_norway

from conftest import MET_RAW

CITY = {"name": "Porto Alegre", "latitude": -30.03, "longitude": -51.23, "country": "Brasil",
        "country_code": "BR", "state": "Rio Grande do Sul", "timezone": "America/Sao_Paulo", "elevation": 10}


def _alert(id_aviso, event, severity, color, day):
    return {"id_aviso": id_aviso, "descricao": event, "severidade": severity, "aviso_cor": color,
            "inicio": f"{day} 00:00", "fim": f"{day} 23:59", "geocodes": "4314902",
            "riscos": [f"Risco de {event}"], "instrucoes": ["Instrução"]}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(geocoding, "find_city", lambda q, lang="en": CITY)
    monkeypatch.setattr(met_norway, "fetch_raw", lambda lat, lon: MET_RAW)
    monkeypatch.setattr(inmet, "_active_alerts", lambda: [
        ("today", _alert(1, "Tempestade", "Grande Perigo", "#C80000", "2026-10-30")),
        ("future", _alert(2, "Acumulado de Chuva", "Perigo", "#F96602", "2026-10-31")),
        ("future", _alert(3, "Ventos Costeiros", "Perigo Potencial", "#FFFE00", "2026-10-31")),
    ])
    return create_app().test_client()


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Wet Bulb Temperature Calculator" in response.data


def test_city_forecast_with_alerts(client):
    html = client.get("/?city=Porto+Alegre&lang=pt").get_data(as_text=True)
    assert "Previsão do tempo para 7 dias" in html
    assert "Agora" in html
    assert "Baixa pressão" in html          # 1005 hPa
    assert "Trovoada" in html               # pior condição do dia 30
    assert "risk-normal" in html            # cor do card de bulbo úmido
    assert "Avisos meteorológicos do INMET" not in html
    for removed in ("Tornado", "Rajadas", "None"):
        assert removed not in html


def _section(html, start, end):
    return html[html.index(start):html.index(end, html.index(start))]


def test_today_alert_is_in_now_card(client):
    html = client.get("/?city=Porto+Alegre&lang=pt").get_data(as_text=True)
    now_card = _section(html, 'class="md-card current-main"', 'wet-bulb-card')
    assert "Tempestade" in now_card and "Grande Perigo" in now_card
    assert 'class="alert-tag"' in now_card
    assert "Acumulado de Chuva" not in now_card


def test_future_alerts_side_by_side_on_their_day(client):
    html = client.get("/?city=Porto+Alegre&lang=pt").get_data(as_text=True)
    today = _section(html, 'id="day-panel-1"', 'class="day ')
    assert "alert-badge" not in today       # aviso de hoje fica só no card "Agora"
    day2 = html[html.index('style="--i: 1"'):html.index('style="--i: 2"')]
    summary = _section(day2, 'class="day-icons"', '</button>')
    assert summary.count('class="alert-badge"') == 2   # dois ícones lado a lado na linha fechada
    tile = _section(day2, 'tile-alerts', 'Bulbo úmido máx.')
    assert tile.count('class="alert-badge"') == 2      # e no mesmo card quando aberto
    assert "Acumulado de Chuva" in tile and "Ventos Costeiros" in tile
    assert 'tabindex="0"' in tile and 'tabindex="0"' not in summary


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
    ("RS", {"country_code": "BR", "admin1": "", "state_code": "BR-RS"}, True),
    ("RS", {"country_code": "BR", "admin1": "Santa Catarina"}, False),
    ("RS", {"country_code": "RS", "admin1": "Belgrade"}, True),
    ("Oklahoma", {"country_code": "US", "admin1": "Oklahoma"}, True),
    ("Oklahoma", {"country_code": "US", "admin1": "Texas"}, False),
    ("brasil", {"country_code": "BR", "country": "Brasil"}, True),
])
def test_matches_region(region, result, expected):
    assert geocoding._matches_region(result, region) is expected


NOMINATIM = [
    {"name": "Santa Maria", "lat": "34.95", "lon": "-120.43", "addresstype": "city",
     "address": {"state": "Califórnia", "country": "Estados Unidos", "country_code": "us", "ISO3166-2-lvl4": "US-CA"}},
    {"name": "Santa Maria", "lat": "-29.68", "lon": "-53.80", "addresstype": "city",
     "address": {"state": "Rio Grande do Sul", "country": "Brasil", "country_code": "br", "ISO3166-2-lvl4": "BR-RS"}},
    {"name": "Santa Maria", "lat": "-5.83", "lon": "-35.69", "addresstype": "municipality",
     "address": {"state": "Rio Grande do Norte", "country": "Brasil", "country_code": "br", "ISO3166-2-lvl4": "BR-RN"}},
]


def test_find_city_with_nominatim_and_uf(monkeypatch):
    geocoding.find_city.cache_clear()
    monkeypatch.setattr(geocoding, "get_json", lambda url, params: NOMINATIM)
    city = geocoding.find_city("Santa Maria, RS", "pt")
    assert (city["state"], city["country_code"]) == ("Rio Grande do Sul", "BR")
    assert city["timezone"] == "America/Sao_Paulo"
    assert geocoding.find_city("Santa Maria", "pt")["country_code"] == "US"  # mais importante primeiro
    assert geocoding.find_city("Santa Maria, RN", "pt")["timezone"] == "America/Fortaleza"
