"""
Modelo de risco à vida do WYW (SPEC.md, seção 4).

Avalia a hora atual e as 3 seguintes (h0 a h3). Cada horário é um dict com:
temp, rh, tw (calculado de temp e rh se ausente), cloud, sun_up, thunder,
wind_kmh, gust_kmh, tornado e alerts ([{event, severity, inside_polygon}]).
Os mesmos casos de teste (spec/risk-cases.json) valem para os motores em
JavaScript e Kotlin.
"""
from flask_babel import lazy_gettext as _l

from ..services.text import normalize
from .wetbulb import calculate_wet_bulb

HEAT_SUN_C = 35            # IND-CALOR, variante sol: acima de 35 °C com sol
HEAT_SHADE_C = 38          # IND-CALOR, variante sombra: acima de 38 °C
SUN_MAX_CLOUD = 75         # nebulosidade abaixo da qual há exposição ao sol (%)
WET_BULB_C = 31            # IND-TW: nível "Perigo" do bulbo úmido
WIND_KMH = 60              # IND-VENTO: acima de 60 km/h
THUNDER_CODES = range(95, 100)
STRONG_ALERT = {"perigo", "grande perigo"}
SEVERITY_RANK = {"perigo potencial": 1, "perigo": 2, "grande perigo": 3}

HEAT, WET_BULB, STORM, WIND, TORNADO = "IND-CALOR", "IND-TW", "IND-TEMP", "IND-VENTO", "IND-TORNADO"
# Ordem de exibição das descrições
ORDER = (TORNADO, WET_BULB, HEAT, STORM, WIND)


def _alerts(hour, *events):
    return [a for a in hour.get("alerts") or [] if normalize(a.get("event")) in events]


def _wet_bulb(hour):
    if hour.get("tw") is not None:
        return hour["tw"]
    return calculate_wet_bulb(hour.get("temp"), hour.get("rh"))


def _heat(hour):
    temp = hour.get("temp")
    if temp is None:
        return None
    if temp > HEAT_SHADE_C:
        return "sombra"
    sunny = hour.get("sun_up") and (hour.get("cloud") if hour.get("cloud") is not None else 0) < SUN_MAX_CLOUD
    return "sol" if temp > HEAT_SUN_C and sunny else None


def _wind(hour):
    """(ativo, velocidade máxima em km/h, aviso que ativou)."""
    speeds = [v for v in (hour.get("wind_kmh"), hour.get("gust_kmh")) if v is not None]
    top = max(speeds) if speeds else None
    alerts = [a for a in _alerts(hour, "vendaval") if normalize(a.get("severity")) in STRONG_ALERT]
    alerts += [a for a in _alerts(hour, "ventos costeiros")
               if normalize(a.get("severity")) in STRONG_ALERT and a.get("inside_polygon")]
    return (top is not None and top > WIND_KMH) or bool(alerts), top, (alerts[0] if alerts else None)


def evaluate(hours, open_meteo=True):
    """
    Nível de risco da janela.

    Retorna {"level": none|attention|life|extreme, "indicators": {ID: detalhes},
    "life_hours": [índices com 2+ indicadores], "tornado_info": "moderate"|None,
    "tornado_available": bool}.
    """
    indicators = {}
    life_hours = []
    tornado_info = None

    def mark(ind, i, **details):
        entry = indicators.setdefault(ind, {"hours": []})
        entry["hours"].append(i)
        for key, value in details.items():
            if value is None:
                continue
            if key.startswith("max_"):
                entry[key] = max(entry.get(key, value), value)
            else:
                entry.setdefault(key, value)

    for i, hour in enumerate(hours):
        active = set()

        variant = _heat(hour)
        if variant:
            active.add(HEAT)
            mark(HEAT, i, max_temp=hour["temp"])
            # A variante sombra (mais grave) prevalece na janela
            if variant == "sombra" or "variant" not in indicators[HEAT]:
                indicators[HEAT]["variant"] = variant

        tw = _wet_bulb(hour)
        if tw is not None and tw >= WET_BULB_C:
            active.add(WET_BULB)
            mark(WET_BULB, i, max_tw=tw)

        storm_alerts = _alerts(hour, "tempestade")
        if hour.get("thunder") or storm_alerts:
            active.add(STORM)
            severity = max((a.get("severity", "") for a in storm_alerts),
                           key=lambda s: SEVERITY_RANK.get(normalize(s), 0), default=None)
            mark(STORM, i, alert_severity=severity)

        wind_active, top, wind_alert = _wind(hour)
        if wind_active:
            active.add(WIND)
            mark(WIND, i, max_kmh=top if top is not None and top > WIND_KMH else None,
                 alert=f"{wind_alert['event']} ({wind_alert['severity']})" if wind_alert else None)

        tornado = hour.get("tornado")
        if tornado == "high":
            mark(TORNADO, i)
        elif tornado == "moderate":
            tornado_info = "moderate"

        if len(active) >= 2:
            life_hours.append(i)

    if TORNADO in indicators:
        level = "extreme"
    elif life_hours:
        level = "life"
    elif indicators:
        level = "attention"
    else:
        level = "none"
    if TORNADO in indicators:
        tornado_info = None  # o indicador extremo substitui o ícone informativo
    return {"level": level, "indicators": indicators, "life_hours": life_hours,
            "tornado_info": tornado_info, "tornado_available": bool(open_meteo)}


def _when(hours, indexes):
    labels = [hours[i].get("label", f"h{i}") for i in indexes]
    if len(labels) == 1:
        return _l("at %(hour)s", hour=labels[0])
    return _l("between %(start)s and %(end)s", start=labels[0], end=labels[-1])


def describe(result, hours):
    """Uma linha por indicador ativo, com valor e horário (SPEC.md 4.5)."""
    lines = []
    for ind in ORDER:
        entry = result["indicators"].get(ind)
        if not entry:
            continue
        when = _when(hours, entry["hours"])
        if ind == TORNADO:
            lines.append(_l("Possibility of a tornado %(when)s", when=when))
        elif ind == WET_BULB:
            lines.append(_l("Wet bulb temperature up to %(value)s °C %(when)s",
                            value=round(entry["max_tw"]), when=when))
        elif ind == HEAT:
            lines.append(_l("Air temperature up to %(value)s °C %(when)s",
                            value=round(entry["max_temp"]), when=when))
        elif ind == STORM:
            if entry.get("alert_severity"):
                lines.append(_l("Thunderstorm expected %(when)s (INMET alert: %(severity)s)",
                                when=when, severity=entry["alert_severity"]))
            else:
                lines.append(_l("Thunderstorm expected %(when)s", when=when))
        elif ind == WIND:
            if entry.get("max_kmh") is not None:
                lines.append(_l("Wind up to %(value)s km/h %(when)s", value=round(entry["max_kmh"]), when=when))
            else:
                lines.append(_l("Strong wind %(when)s (INMET alert: %(alert)s)", when=when, alert=entry["alert"]))
    return [str(line) for line in lines]


def heat_recommendation(result):
    """Recomendação de IND-CALOR (SPEC.md 4.2, D-3), ou None."""
    entry = result["indicators"].get(HEAT)
    if not entry:
        return None
    if entry["variant"] == "sombra":
        return _l("Unhealthy heat even in the shade: if you are outdoors, go to a cool or air-conditioned place.")
    return _l("If you are outdoors and in the sun, get out of the sun and look for shade or a cool place.")
