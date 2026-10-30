import logging

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_babel import gettext as _

from . import get_locale
from .services import forecast, geocoding, inmet
from .services.http import ServiceError

bp = Blueprint("main", __name__)
log = logging.getLogger(__name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    # Mantém compatibilidade com o formulário antigo (POST) redirecionando para GET.
    if request.method == "POST":
        return redirect(url_for("main.index", city=request.form.get("city", "")))

    query = (request.args.get("city") or "").strip()
    if not query:
        return render_template("index.html")

    try:
        city = geocoding.find_city(query, get_locale())
        weather = forecast.get_weather(city["latitude"], city["longitude"], city["timezone"])
    except geocoding.CityNotFound:
        return render_template("index.html", query=query,
                               error=_("City not found. Try adding the country code, e.g. \"Paris, FR\"."))
    except ServiceError as exc:
        log.exception("Falha ao obter dados meteorológicos")
        return render_template("index.html", query=query,
                               error=_("Weather service unavailable. Please try again later.")), 503

    alerts = None
    if city["country_code"] == "BR":
        alerts = inmet.get_alerts_for_city(city["name"], city["state"], city["latitude"], city["longitude"])

    return render_template("index.html", query=query, city=city, weather=weather, alerts=alerts)


@bp.route("/change-language")
def change_language():
    lang = request.args.get("lang")
    if lang in current_app.config["BABEL_SUPPORTED_LOCALES"]:
        session["lang"] = lang
    target = request.referrer if request.referrer and request.referrer.startswith(request.host_url) else None
    return redirect(target or url_for("main.index"))
