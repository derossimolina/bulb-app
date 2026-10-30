"""Índices derivados: sistema de pressão (alta/normal/baixa) e tendência."""
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

