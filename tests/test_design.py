"""Design system no site: J. de Rossi Molina, marca jeronimo molina (SPEC.md seção 5; DESIGN.md v4.1.0)."""
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
    assert "family=Manrope:wght@600;700&family=Inter:wght@400;600&family=JetBrains+Mono:wght@500" in html
    # Ícones Lucide do sprite local; nada de Font Awesome (DESIGN.md 2.6)
    assert "font-awesome" not in html and "fa-solid" not in html
    assert "/static/icons.svg#cloud-lightning" in html or "/static/icons.svg#cloud-sun" in html


def test_icon_sprite_has_every_icon_used_in_templates_and_code():
    root = Path(__file__).resolve().parent.parent / "app"
    sprite = (root / "static" / "icons.svg").read_text(encoding="utf-8")
    symbols = set(re.findall(r'<symbol id="([\w-]+)"', sprite))
    used = set()
    for path in list((root / "templates").rglob("*.html")):
        # Nomes montados no template ("brand-" ~ marca) são conferidos em test_footer_has_company_site_...
        used |= {n for n in re.findall(r"icon\('([\w-]+)'", path.read_text(encoding="utf-8")) if not n.endswith("-")}
    used |= set(re.findall(r"icon\('([\w-]+)'", (root / "static" / "wyw.js").read_text(encoding="utf-8")))
    from app.meteo import wetbulb, wmo
    used |= {icon for _, icon in wmo.WMO_CODES.values()} | {wmo.DEFAULT_ICON}
    used |= {level[3] for level in wetbulb.WET_BULB_LEVELS} | {"leaf"}
    assert used and used <= symbols, used - symbols


def test_footer_has_brand_logo_in_both_themes(monkeypatch):
    html = _page(monkeypatch, "/?lang=pt")
    footer = html[html.index("<footer>"):html.index("</footer>")]
    assert "brand/jeronimo-lockup-principal.svg" in footer and "brand/jeronimo-lockup-principal-claro.svg" in footer
    assert 'alt="jeronimo molina"' in footer and "https://jeronimo.caxias.br" in footer
    assert "J. de Rossi Molina Ltda" in footer


def test_no_emoji_in_the_interface(monkeypatch):
    # Exceções do REQ-DS-06 (ícones do INMET, bandeiras) são imagens, não emoji
    assert not EMOJI.search(_page(monkeypatch))
    assert not EMOJI.search(_page(monkeypatch, "/?lang=pt"))


def test_theme_toggle_and_saved_theme(monkeypatch):
    html = _page(monkeypatch, "/?lang=pt")
    assert 'id="theme-toggle"' in html and "Alternar entre tema claro e escuro" in html
    assert "localStorage.getItem('wyw-theme')" in html
    assert '<meta name="color-scheme" content="dark light">' in html


def test_css_defines_both_themes_with_design_system_tokens():
    assert "@media (prefers-color-scheme: dark)" in CSS
    assert ':root[data-theme="dark"]' in CSS
    # Escuro é a base (:root); claro é o reverso (DESIGN.md 2.1)
    dark = CSS[CSS.index(":root{"):CSS.index("}", CSS.index(":root{"))]
    for token in ("--fundo:#100C08", "--tinta:#F3F4F5", "--texto-2:#DBE0E1", "--texto-3:#9AA0A3", "--linha:#2B2620",
                  "--acento:#FB5133", "--acento-hover:#FF6B4F", "--erro:#FF6B8B", "--alerta:#FFD24D"):
        assert token in dark
    light = CSS[CSS.index(':root[data-theme="light"]{'):]
    for token in ("--fundo:#F3F4F5", "--tinta:#100C08", "--texto-3:#5E6366", "--acento:#C93414", "--alerta:#7A5200"):
        assert token in light
    # Azul e vermelho só como temperatura e alerta (frio, quente, risco)
    assert "--frio:" in dark and "--quente:" in dark and "--risco:#B3261E" in dark
    # Raio único de 8 px; só os pontos e o indicador são circulares
    radii = {r.strip() for r in re.findall(r"border-radius:([^;}]+)", CSS)}
    assert radii <= {"var(--raio)", "50%"} and "--raio:8px" in CSS
    assert "box-shadow" not in CSS
    # Movimento: nenhuma transição de interface passa de 400 ms
    for value in re.findall(r"(\d*\.?\d+)(ms|s)\b", CSS):
        ms = float(value[0]) * (1 if value[1] == "ms" else 1000)
        assert ms <= 1200   # 1,2 s só no laço do indicador de carregamento


SOCIAL = {
    "brand-instagram": "https://www.instagram.com/jderossimolina",
    "brand-youtube": "https://www.youtube.com/@jderossimolina",
    "brand-tiktok": "https://www.tiktok.com/@jderossimolina",
    "brand-x": "https://x.com/jdermolina",
    "brand-facebook": "https://www.facebook.com/jderossimolina",
    "brand-linkedin": "https://www.linkedin.com/in/molinajeronimo",
    "brand-github": "https://github.com/jeronimo-molina",
}


def test_footer_has_company_site_social_icons_and_wet_bulb_page(monkeypatch):
    html = _page(monkeypatch, "/?lang=pt")
    footer = html[html.index("<footer>"):html.index("</footer>")]
    assert 'href="/sobre-bulbo-umido"' in footer and "Sobre bulbo úmido" in footer
    assert 'href="https://jeronimo.caxias.br"' in footer and "jeronimo.caxias.br</a>" in footer
    sprite = (Path(__file__).resolve().parent.parent / "app" / "static" / "icons.svg").read_text(encoding="utf-8")
    for icon, url in SOCIAL.items():
        assert f'href="{url}"' in footer and f"icons.svg#{icon}" in footer
        assert f'<symbol id="{icon}"' in sprite
    # Ícone sozinho precisa de nome acessível (DESIGN.md 2.6)
    assert footer.count('role="img" aria-label="') >= len(SOCIAL)


def test_search_button_and_wet_bulb_text_moved_to_its_own_page(monkeypatch):
    html = _page(monkeypatch, "/?lang=pt")
    assert "Veja a previsão do tempo" in html
    assert "O que é temperatura de bulbo úmido?" not in html


def test_wet_bulb_page(monkeypatch):
    html = _page(monkeypatch, "/sobre-bulbo-umido?lang=pt")
    assert "<title>Sobre bulbo úmido · WYW</title>" in html
    assert "O que é temperatura de bulbo úmido?" in html and "10.1073/pnas.0913352107" in html
    # Os quatro níveis, com os limites de app/meteo/wetbulb.py (SPEC.md 4.3)
    for limit in ("&lt; 23 °C", "23–31 °C", "31–35 °C", "≥ 35 °C"):
        assert limit in html
    assert "Temperatura normal." in html and 'href="/"' in html
