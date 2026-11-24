import logging

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_babel import gettext as _

from . import get_locale
from .meteo import wetbulb
from .services import forecast, geocoding, inmet, risk_window
from .services.http import ServiceError

bp = Blueprint("main", __name__)
log = logging.getLogger(__name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    # Mantém compatibilidade com o formulário antigo (POST) redirecionando para GET.
    if request.method == "POST":
        return redirect(url_for("main.index", city=request.form.get("city", "")))

    query = (request.args.get("city") or "").strip()
    has_coordinates = request.args.get("lat") and request.args.get("lon")
    if not query and not has_coordinates:
        return render_template("index.html")

    try:
        if has_coordinates:
            # Busca por endereço: o navegador já geocodificou (SPEC.md REQ-WEB-11)
            city = geocoding.place_from_coordinates(
                request.args["lat"], request.args["lon"], query,
                request.args.get("state", ""), request.args.get("cc", ""))
        else:
            city = geocoding.find_city(query, get_locale())
        weather = forecast.get_weather(city["latitude"], city["longitude"], city["timezone"])
    except (geocoding.CityNotFound, ValueError):
        return render_template("index.html", query=query,
                               error=_("City not found. Try adding the country code, e.g. \"Paris, FR\"."))
    except ServiceError as exc:
        log.exception("Falha ao obter dados meteorológicos")
        return render_template("index.html", query=query,
                               error=_("Weather service unavailable. Please try again later.")), 503

    alerts = None
    if city["country_code"] == "BR":
        alerts = inmet.get_alerts_for_city(city["name"], city["state"], city["latitude"], city["longitude"])
        # Avisos de hoje ficam no card "Agora"; os dos outros dias, no dia correspondente da previsão
        by_date = inmet.alerts_by_date(alerts["alerts"])
        today = weather["daily"][0]["date"] if weather["daily"] else None
        weather["current"]["alerts"] = by_date.get(today, [])
        for day in weather["daily"][1:]:
            day["alerts"] = by_date.get(day["date"], [])

    # Nível de risco à vida nas próximas 3 horas (SPEC.md seção 4)
    weather["risk"] = risk_window.assess(weather, city["latitude"], city["longitude"],
                                         alerts["alerts"] if alerts else ())

    client = risk_window.client_data(city, weather)
    return render_template("index.html", query=query, city=city, weather=weather, alerts=alerts, client=client)


@bp.route("/healthz")
def healthz():
    # Para o monitoramento: não chama serviços externos (SPEC.md 8.1)
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store"}


@bp.route("/sobre-bulbo-umido")
def about_wet_bulb():
    """Página "Sobre bulbo úmido" (link no rodapé): o que é, para que serve e os níveis de risco (SPEC.md 4.3)."""
    levels = [{"key": "normal", "from": None, "to": wetbulb.WET_BULB_LEVELS[-1][0], "message": _("Normal temperature.")}]
    for threshold, key, _color, _icon, message in reversed(wetbulb.WET_BULB_LEVELS):
        levels.append({"key": key, "from": threshold, "to": None, "message": message})
    for level, nxt in zip(levels[1:], levels[2:] + [None]):
        level["to"] = nxt["from"] if nxt else None
    return render_template("wet_bulb.html", levels=levels)


@bp.route("/manifest.webmanifest")
def manifest():
    """Manifesto do app instalável (PWA), no idioma da página: alternativa ao app Android até ele sair."""
    icons = [
        {"src": url_for("static", filename="pwa/icon-192.png"), "sizes": "192x192", "type": "image/png"},
        {"src": url_for("static", filename="pwa/icon-512.png"), "sizes": "512x512", "type": "image/png"},
        {"src": url_for("static", filename="pwa/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png",
         "purpose": "maskable"},
    ]
    response = jsonify({
        "id": "/",
        "name": "WYW — Weather is your Weather",
        "short_name": "WYW",
        "description": _("Wet bulb temperature, risk to life, tornado alert and 7-day forecast for your city."),
        "lang": get_locale(),
        "start_url": url_for("main.index", source="pwa"),
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#100C08",
        "theme_color": "#100C08",
        "categories": ["weather"],
        "icons": icons,
    })
    response.mimetype = "application/manifest+json"
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.route("/sw.js")
def service_worker():
    # Na raiz, para o service worker controlar o site inteiro (escopo "/")
    response = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript", max_age=0)
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.route("/offline")
def offline():
    """Página mostrada pelo app instalado quando não há conexão (guardada pelo service worker)."""
    return render_template("offline.html")


@bp.route("/change-language")
def change_language():
    lang = request.args.get("lang")
    if lang in current_app.config["BABEL_SUPPORTED_LOCALES"]:
        session["lang"] = lang
    target = request.referrer if request.referrer and request.referrer.startswith(request.host_url) else None
    return redirect(target or url_for("main.index"))
