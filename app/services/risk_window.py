"""
Monta a janela de risco (hora atual + 3 seguintes) a partir da série horária do
MET Norway e dos avisos do INMET, no formato de app/meteo/risk.py.
"""
import datetime
from zoneinfo import ZoneInfo

from flask_babel import gettext as _

from ..meteo import risk
from ..meteo.sun import is_sun_up

WINDOW_HOURS = 4                      # h0 a h3
MS_TO_KMH = 3.6
INMET_TZ = ZoneInfo("America/Sao_Paulo")   # horários dos avisos do INMET (Brasília)
ONE_HOUR = datetime.timedelta(hours=1)


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _alert_period(alert):
    try:
        start = datetime.datetime.fromisoformat(str(alert["start"])).replace(tzinfo=INMET_TZ)
        end = datetime.datetime.fromisoformat(str(alert["end"])).replace(tzinfo=INMET_TZ)
    except (KeyError, TypeError, ValueError):
        return None
    return start, end


def build_hours(hourly, latitude, longitude, alerts=(), now=None):
    """Lista de horários para risk.evaluate (até 4, de hora em hora)."""
    now = now or _now()
    periods = [(a, _alert_period(a)) for a in alerts]
    times = hourly.get("time_utc", [])

    def col(name, i):
        series = hourly.get(name) or []
        return series[i] if i < len(series) else None

    hours = []
    previous = None
    for i, stamp in enumerate(times):
        start = datetime.datetime.fromisoformat(stamp)
        if start + ONE_HOUR <= now:
            continue  # horário já passou
        if previous is not None and start - previous > ONE_HOUR:
            break     # a série deixou de ser horária
        local = datetime.datetime.fromisoformat(hourly["time"][i])
        wind = col("wind_speed_10m", i)
        code = col("weather_code", i)
        hours.append({
            "label": _("%(hour)s:00", hour=local.hour),
            "temp": col("temperature_2m", i),
            "rh": col("relative_humidity_2m", i),
            "cloud": col("cloud_cover", i),
            "sun_up": is_sun_up(latitude, longitude, start),
            "thunder": code is not None and code in risk.THUNDER_CODES,
            "wind_kmh": wind * MS_TO_KMH if wind is not None else None,
            "gust_kmh": None,     # Open-Meteo, pelo navegador (M2)
            "tornado": None,      # Open-Meteo, pelo navegador (M2)
            "alerts": [
                {"event": a["event"], "severity": a["severity"], "inside_polygon": a.get("inside_polygon", False)}
                for a, period in periods
                if period and period[0] < start + ONE_HOUR and period[1] >= start
            ],
        })
        previous = start
        if len(hours) == WINDOW_HOURS:
            break
    return hours


def assess(weather, latitude, longitude, alerts=(), now=None):
    """Risco da janela pronto para o template (SPEC.md 3.5 e 4.5)."""
    hours = build_hours(weather.get("hourly", {}), latitude, longitude, alerts, now)
    if not hours:
        return None
    # Até o M2, rajadas e tornado (Open-Meteo pelo navegador) não estão disponíveis
    result = risk.evaluate(hours, open_meteo=False)
    result["lines"] = risk.describe(result, hours)
    result["recommendation"] = risk.heat_recommendation(result)
    result["window"] = (hours[0]["label"], hours[-1]["label"])
    return result
