"""Temperatura de bulbo úmido e níveis de risco associados."""
import math

from flask_babel import lazy_gettext as _l


def calculate_wet_bulb(temp, humidity):
    """
    Temperatura de bulbo úmido (°C) pela fórmula empírica de Stull (2011).

    Válida para umidade relativa entre 5% e 99% e temperatura entre -20 °C e 50 °C,
    com erro típico inferior a 1 °C.
    """
    if temp is None or humidity is None:
        return None
    rh = min(max(float(humidity), 5.0), 99.0)
    t = float(temp)
    wet_bulb = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * math.pow(rh, 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )
    return round(wet_bulb, 1)


# Limiares baseados em Sherwood & Huber (2010) e literatura de estresse térmico.
WET_BULB_LEVELS = [
    (35, "extreme", "red", "fa-skull-crossbones",
     _l("Life risk! Seek an air-conditioned place immediately!")),
    (31, "danger", "orange", "fa-exclamation-triangle",
     _l("Danger! Seek an air-conditioned place. Risk of life for sensitive people.")),
    (23, "alert", "yellow", "fa-exclamation-circle",
     _l("Alert! Look for a cool place.")),
]


def wet_bulb_risk(wet_bulb_temp):
    """Retorna o nível de risco (chave, cor, ícone e mensagem) para a temperatura de bulbo úmido."""
    if wet_bulb_temp is not None:
        for threshold, key, color, icon, message in WET_BULB_LEVELS:
            if wet_bulb_temp >= threshold:
                return {"key": key, "color": color, "icon": icon, "message": message}
    return {"key": "normal", "color": "green", "icon": "fa-leaf", "message": _l("Normal temperature.")}
