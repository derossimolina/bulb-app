"""App instalável (PWA), alternativa ao app Android até ele estar disponível."""
import json

from app import create_app
from app.services import geocoding, inmet, met_norway

from conftest import MET_RAW

CITY = {"name": "Porto Alegre", "latitude": -30.03, "longitude": -51.23, "country": "Brasil",
        "country_code": "BR", "state": "Rio Grande do Sul", "timezone": "America/Sao_Paulo"}


def _client():
    return create_app().test_client()


def test_manifest_is_installable_and_localized():
    response = _client().get("/manifest.webmanifest?lang=pt")
    assert response.status_code == 200
    assert response.mimetype == "application/manifest+json"
    data = json.loads(response.get_data(as_text=True))
    assert data["display"] == "standalone" and data["scope"] == "/" and data["short_name"] == "WYW"
    assert data["start_url"].startswith("/")
    assert data["lang"] == "pt" and "alerta de tornado" in data["description"]
    sizes = {(icon["sizes"], icon.get("purpose", "any")) for icon in data["icons"]}
    assert {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= sizes
    for icon in data["icons"]:
        assert _client().get(icon["src"]).status_code == 200


def test_service_worker_is_served_from_the_root():
    response = _client().get("/sw.js")
    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    assert "no-cache" in response.headers["Cache-Control"]
    body = response.get_data(as_text=True)
    assert "'/offline'" in body
    # As APIs de tempo e avisos nunca são guardadas: só o próprio site e as fontes
    assert "api.open-meteo.com" not in body and "nominatim.openstreetmap.org" not in body


def test_offline_page():
    html = _client().get("/offline?lang=pt").get_data(as_text=True)
    assert "Sem conexão:" in html and "Tentar de novo" in html


def test_pages_link_manifest_install_card_and_offline_bar(monkeypatch):
    monkeypatch.setattr(geocoding, "find_city", lambda q, lang="en": CITY)
    monkeypatch.setattr(met_norway, "fetch_raw", lambda lat, lon: MET_RAW)
    monkeypatch.setattr(inmet, "_active_alerts", lambda: [])
    html = _client().get("/?city=Porto+Alegre&lang=pt").get_data(as_text=True)
    assert '<link rel="manifest" href="/manifest.webmanifest">' in html
    assert 'rel="apple-touch-icon"' in html and 'name="theme-color"' in html
    assert 'id="install-card"' in html and "O app para Android ainda não está disponível" in html
    assert 'id="offline-bar"' in html and "WYW.setupApp()" in html
