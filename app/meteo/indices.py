"""
Índices derivados: sistema de pressão e potencial de tornado.

O indicador de tornado é uma estimativa experimental baseada em parâmetros
de ambiente convectivo (CAPE, cisalhamento do vento e índice de levantamento).
Ele NÃO substitui avisos oficiais de órgãos meteorológicos.
"""
import math

from flask_babel import lazy_gettext as _l

# Pressão ao nível do mar (hPa)
HIGH_PRESSURE_HPA = 1020
LOW_PRESSURE_HPA = 1008
PRESSURE_TREND_HPA = 3


def classify_pressure(pressure_hpa, previous_hpa=None):
    """Classifica a pressão ao nível do mar em alta/normal/baixa e calcula a tendência."""
    if pressure_hpa is None:
        return None
    if pressure_hpa >= HIGH_PRESSURE_HPA:
        level = {"key": "high", "label": _l("High pressure"), "symbol": "A",
                 "hint": _l("Stable weather, few clouds")}
    elif pressure_hpa <= LOW_PRESSURE_HPA:
        level = {"key": "low", "label": _l("Low pressure"), "symbol": "B",
                 "hint": _l("Unstable weather, clouds and rain likely")}
    else:
        level = {"key": "normal", "label": _l("Normal pressure"), "symbol": "≈",
                 "hint": _l("No dominant pressure system")}

    trend = None
    if previous_hpa is not None:
        delta = pressure_hpa - previous_hpa
        if delta >= PRESSURE_TREND_HPA:
            trend = {"key": "rising", "arrow": "↑", "label": _l("Rising")}
        elif delta <= -PRESSURE_TREND_HPA:
            trend = {"key": "falling", "arrow": "↓", "label": _l("Falling")}
        else:
            trend = {"key": "steady", "arrow": "→", "label": _l("Steady")}

    return {**level, "value": round(pressure_hpa, 1), "trend": trend}


def _wind_vector(speed, direction_deg):
    """Converte velocidade (m/s) e direção meteorológica (graus) em componentes u, v."""
    rad = math.radians(direction_deg)
    return -speed * math.sin(rad), -speed * math.cos(rad)


def bulk_shear(speed_low, dir_low, speed_high, dir_high):
    """Magnitude do cisalhamento vetorial do vento entre dois níveis (m/s)."""
    if None in (speed_low, dir_low, speed_high, dir_high):
        return None
    u1, v1 = _wind_vector(speed_low, dir_low)
    u2, v2 = _wind_vector(speed_high, dir_high)
    return math.hypot(u2 - u1, v2 - v1)


TORNADO_LEVELS = {
    "very_low": {"rank": 0, "label": _l("Very low"), "color": "green"},
    "low": {"rank": 1, "label": _l("Low"), "color": "light-green"},
    "moderate": {"rank": 2, "label": _l("Moderate"), "color": "orange"},
    "high": {"rank": 3, "label": _l("High"), "color": "red"},
}


def tornado_potential_hour(cape, lifted_index, deep_shear, low_shear):
    """
    Classifica o potencial de tornado para um horário.

    Usa o parâmetro WMAXSHEAR = sqrt(2·CAPE) × cisalhamento 0–6 km
    (Taszarek et al., 2020), refinado pelo cisalhamento em baixos níveis
    (superfície–850 hPa) e pelo índice de levantamento (LI).
    Cisalhamento profundo: superfície–500 hPa (≈ 0–5,5 km).
    """
    if cape is None or deep_shear is None:
        return "very_low", 0.0
    wmaxshear = math.sqrt(2 * max(cape, 0)) * deep_shear
    low_shear = low_shear or 0
    li = lifted_index if lifted_index is not None else 0

    if cape < 100 or wmaxshear < 400:
        level = "very_low"
    elif wmaxshear >= 1200 and low_shear >= 12 and li <= -4:
        level = "high"
    elif wmaxshear >= 800 and low_shear >= 8:
        level = "moderate"
    else:
        level = "low"
    return level, round(wmaxshear)


def tornado_potential_day(hours):
    """
    Potencial de tornado diário (pior horário do dia).

    `hours` é uma lista de dicts com cape, lifted_index, deep_shear e low_shear.
    """
    worst_level, worst_index, worst_cape = "very_low", 0.0, 0.0
    for h in hours:
        level, index = tornado_potential_hour(
            h.get("cape"), h.get("lifted_index"), h.get("deep_shear"), h.get("low_shear")
        )
        if (TORNADO_LEVELS[level]["rank"], index) > (TORNADO_LEVELS[worst_level]["rank"], worst_index):
            worst_level, worst_index, worst_cape = level, index, h.get("cape") or 0
    return {"key": worst_level, **TORNADO_LEVELS[worst_level],
            "wmaxshear": worst_index, "cape": round(worst_cape)}
