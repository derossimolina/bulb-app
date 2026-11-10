import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    # Idioma padrão de cada domínio, quando a pessoa não escolheu um (SPEC.md REQ-WEB-04)
    DOMAIN_LOCALES = {"clima.derossi.dev": "pt", "weather.derossi.dev": "en"}
    DEFAULT_DOMAIN = "weather.derossi.dev"   # hreflang="x-default"
    # Endereço novo do site: quando definido, tudo responde 301 para ele (SPEC.md REQ-INFRA-06)
    REDIRECT_TO = os.getenv("REDIRECT_TO", "")
    # Quantos proxies à frente do app são confiáveis (1 atrás do Caddy; 0 ignora os cabeçalhos X-Forwarded-*)
    TRUSTED_PROXIES = int(os.getenv("TRUSTED_PROXIES", "0"))
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_SUPPORTED_LOCALES = ["en", "pt", "es"]
    BABEL_TRANSLATION_DIRECTORIES = "translations"
