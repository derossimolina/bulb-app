"""Idioma padrão por domínio, hreflang e canonical (SPEC.md REQ-WEB-04, AC-WEB-04)."""
import pytest

from app import create_app

CLIMA = "https://clima.derossi.dev"
WEATHER = "https://weather.derossi.dev"


@pytest.fixture
def client():
    return create_app().test_client()


def _html(client, host, path="/", **headers):
    return client.get(path, base_url=f"https://{host}", headers=headers).get_data(as_text=True)


def test_clima_abre_em_portugues_mesmo_com_navegador_em_ingles(client):
    assert '<html lang="pt">' in _html(client, "clima.derossi.dev", **{"Accept-Language": "en-US,en;q=0.9"})


def test_weather_abre_em_ingles_mesmo_com_navegador_em_portugues(client):
    assert '<html lang="en">' in _html(client, "weather.derossi.dev", **{"Accept-Language": "pt-BR,pt;q=0.9"})


def test_parametro_lang_vence_o_dominio(client):
    assert '<html lang="es">' in _html(client, "weather.derossi.dev", "/?lang=es")


def test_escolha_salva_na_sessao_vence_o_dominio(client):
    client.get("/change-language?lang=pt", base_url=WEATHER)

    assert '<html lang="pt">' in _html(client, "weather.derossi.dev")


def test_em_outro_endereco_vale_o_idioma_do_navegador(client):
    assert '<html lang="es">' in _html(client, "bulb-app.onrender.com", **{"Accept-Language": "es-AR,es;q=0.9"})


@pytest.mark.parametrize("host", ["clima.derossi.dev", "weather.derossi.dev"])
def test_hreflang_reciprocos_no_mesmo_caminho(client, host):
    html = _html(client, host)

    assert f'<link rel="alternate" hreflang="pt" href="{CLIMA}/">' in html
    assert f'<link rel="alternate" hreflang="en" href="{WEATHER}/">' in html
    assert f'<link rel="alternate" hreflang="x-default" href="{WEATHER}/">' in html
    assert f'<link rel="canonical" href="https://{host}/">' in html


def test_links_mantem_a_busca_e_descartam_o_parametro_lang(client):
    html = _html(client, "clima.derossi.dev", "/?lang=pt&city=")

    assert f'hreflang="en" href="{WEATHER}/"' in html
    assert "lang=pt" not in html.split("</head>")[0]


def test_links_escapam_a_busca(client, monkeypatch):
    from app.services import geocoding

    def not_found(query, lang="en"):
        raise geocoding.CityNotFound(query)

    monkeypatch.setattr(geocoding, "find_city", not_found)

    head = _html(client, "clima.derossi.dev", '/?city=S%C3%A3o+Paulo%22%3E%3Cb%3E').split("</head>")[0]

    assert f'hreflang="en" href="{WEATHER}/?city=S%C3%A3o+Paulo%22%3E%3Cb%3E"' in head
    assert f'<link rel="canonical" href="{CLIMA}/?city=S%C3%A3o+Paulo%22%3E%3Cb%3E">' in head
    assert "<b>" not in head
