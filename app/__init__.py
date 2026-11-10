"""Wet Bulb Temperature — aplicação Flask."""
import logging

from flask import Flask, redirect, request, session
from flask_babel import Babel
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config


def get_locale():
    from flask import current_app

    supported = current_app.config["BABEL_SUPPORTED_LOCALES"]
    lang = request.args.get("lang") or session.get("lang")
    if lang in supported:
        return lang
    return request.accept_languages.best_match(supported) or current_app.config["BABEL_DEFAULT_LOCALE"]


def create_app(config_object=Config):
    # Avisos e erros dos serviços externos com nível e origem nos logs (Render/gunicorn)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    app = Flask(__name__)
    app.config.from_object(config_object)

    proxies = app.config["TRUSTED_PROXIES"]
    if proxies:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies)

    Babel(app, locale_selector=get_locale)

    @app.before_request
    def redirect_to_new_address():
        target = app.config["REDIRECT_TO"].rstrip("/")
        if target and request.endpoint != "main.healthz":
            query = request.query_string.decode()
            return redirect(target + request.path + ("?" + query if query else ""), code=301)

    @app.context_processor
    def inject_locale():
        return {"get_locale": get_locale}

    from .routes import bp
    app.register_blueprint(bp)
    return app
