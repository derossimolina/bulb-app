"""Rota de saúde, proxy e redirecionamento do endereço antigo (SPEC.md 8.1, REQ-INFRA-02 e 06)."""
from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app
from app.config import Config
from app.services import geocoding, met_norway


def _app(**settings):
    return create_app(type("TestConfig", (Config,), settings))


def test_healthz_responde_sem_chamar_apis(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("a rota de saúde não pode chamar serviços externos")

    monkeypatch.setattr(geocoding, "find_city", fail)
    monkeypatch.setattr(met_norway, "fetch_raw", fail)

    response = _app().test_client().get("/healthz")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert response.headers["Cache-Control"] == "no-store"


def test_sem_redirect_to_a_pagina_inicial_abre():
    assert _app(REDIRECT_TO="").test_client().get("/").status_code == 200


def test_redirect_to_mantem_caminho_e_parametros():
    client = _app(REDIRECT_TO="https://clima.derossi.dev/").test_client()

    response = client.get("/?city=Porto+Alegre&lang=pt")

    assert response.status_code == 301
    assert response.headers["Location"] == "https://clima.derossi.dev/?city=Porto+Alegre&lang=pt"


def test_redirect_to_sem_parametros_nao_deixa_interrogacao():
    client = _app(REDIRECT_TO="https://clima.derossi.dev").test_client()

    assert client.get("/change-language").headers["Location"] == "https://clima.derossi.dev/change-language"


def test_redirect_to_nao_afeta_a_rota_de_saude():
    client = _app(REDIRECT_TO="https://clima.derossi.dev").test_client()

    assert client.get("/healthz").status_code == 200


def test_sem_proxy_confiavel_os_cabecalhos_encaminhados_sao_ignorados():
    app = _app(TRUSTED_PROXIES=0)

    assert not isinstance(app.wsgi_app, ProxyFix)


def test_com_um_proxy_confiavel_vale_o_ip_e_o_esquema_encaminhados():
    app = _app(TRUSTED_PROXIES=1)
    seen = {}

    @app.route("/_eco")
    def eco():
        from flask import request
        seen.update(ip=request.remote_addr, scheme=request.scheme, host=request.host)
        return ""

    # O primeiro IP da lista é forjável por quem acessa; só o último salto (o Caddy) é confiável
    app.test_client().get("/_eco", headers={
        "X-Forwarded-For": "1.2.3.4, 200.10.20.30", "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "clima.derossi.dev"})

    assert seen == {"ip": "200.10.20.30", "scheme": "https", "host": "clima.derossi.dev"}
