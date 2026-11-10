import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    # Idioma padrão de cada domínio, quando a pessoa não escolheu um (SPEC.md REQ-WEB-04)
    DOMAIN_LOCALES = {"clima.derossi.dev": "pt", "weather.derossi.dev": "en"}
    DEFAULT_DOMAIN = "weather.derossi.dev"   # hreflang="x-default"
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_SUPPORTED_LOCALES = ["en", "pt", "es"]
    BABEL_TRANSLATION_DIRECTORIES = "translations"
