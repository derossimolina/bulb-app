"""Design system no site (SPEC.md seção 5: REQ-WEB-03, REQ-DS-01 a 07)."""
import re
from pathlib import Path

from app import create_app
from app.services import geocoding, inmet, met_norway

from conftest import MET_RAW

CSS = (Path(__file__).resolve().parent.parent / "app" / "static" / "style.css").read_text(encoding="utf-8")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
CITY = {"name": "Porto Alegre", "latitude": -30.03, "longitude": -51.23, "country": "Brasil",
        "country_code": "BR", "state": "Rio Grande do Sul", "timezone": "America/Sao_Paulo"}


def _page(monkeypatch, path="/?city=Porto+Alegre&lang=pt"):
    monkeypatch.setattr(geocoding, "find_city", lambda q, lang="en": CITY)
    monkeypatch.setattr(met_norway, "fetch_raw", lambda lat, lon: MET_RAW)
    monkeypatch.setattr(inmet, "_active_alerts", lambda: [])
    return create_app().test_client().get(path).get_data(as_text=True)


def test_design_system_fonts_and_icons_without_materialize(monkeypatch):
    html = _page(monkeypatch)
    assert "materialize" not in html
    assert "family=EB+Garamond:wght@600&family=Inter" in html
    assert "font-awesome/6.5.2" in html
    assert 'class="fa-solid fa-cloud-bolt"' in html or 'class="fa-solid fa-cloud-sun"' in html


def test_no_emoji_in_the_interface(monkeypatch):
    # Exceções do REQ-DS-06 (ícones do INMET, bandeiras) são imagens, não emoji
    assert not EMOJI.search(_page(monkeypatch))
    assert not EMOJI.search(_page(monkeypatch, "/?lang=pt"))


def test_theme_toggle_and_saved_theme(monkeypatch):
    html = _page(monkeypatch, "/?lang=pt")
    assert 'id="theme-toggle"' in html and "Alternar entre tema claro e escuro" in html
    assert "localStorage.getItem('wyw-theme')" in html
    assert '<meta name="color-scheme" content="light dark">' in html


def test_css_defines_both_themes_with_design_system_tokens():
    assert "@media (prefers-color-scheme: dark)" in CSS
    assert ':root[data-theme="dark"]' in CSS
    for token in ("--ink:#0f0e0d", "--ivory:#fafaf9", "--g3:#6b6862", "--marmore:#ede6da",
                  "--ouro:#c9964a", "--bronze:#7a4a22", "--risco-vida:#b3261e", "--alerta-icone:#f5c518"):
        assert token in CSS
    # Cantos retos: só a pílula tem raio (8px) e o spinner é circular
    radii = {r.strip() for r in re.findall(r"border-radius:([^;}]+)", CSS)}
    assert radii <= {"0", "8px", "50%"}
    assert "box-shadow" not in CSS
