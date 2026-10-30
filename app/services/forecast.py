"""
Condições atuais e previsão de 7 dias via MET Norway (veja met_norway.py).

O Open-Meteo foi abandonado: seu limite gratuito é por IP e, no plano Free do
Render, o IP de saída é compartilhado, o que causava erros 429 em produção.
"""
import datetime
from collections import defaultdict

from ..meteo import wmo
from ..meteo.indices import classify_pressure
from ..meteo.wetbulb import calculate_wet_bulb, wet_bulb_risk
from . import met_norway

FORECAST_DAYS = 7
MS_TO_KMH = 3.6


def _round(value, digits=0):
    if value is None:
        return None
    return round(value, digits) if digits else int(round(value))


def _kmh(speed_ms):
    return _round(speed_ms * MS_TO_KMH) if speed_ms is not None else None


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _group_hourly_by_day(hourly):
    """Agrupa as séries horárias por data local (YYYY-MM-DD)."""
    days = defaultdict(list)
    for i, timestamp in enumerate(hourly.get("time", [])):
        row = {key: (series[i] if i < len(series) else None)
               for key, series in hourly.items() if key != "time"}
        days[timestamp[:10]].append(row)
    return days


def build_current(data):
    current = data.get("current", {})
    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    wet_bulb = calculate_wet_bulb(temp, humidity)
    condition, emoji = wmo.describe(current.get("weather_code"))
    return {
        "time": current.get("time"),
        "temperature": _round(temp, 1),
        "apparent_temperature": _round(current.get("apparent_temperature"), 1),
        "dew_point": _round(current.get("dew_point_2m"), 1),
        "humidity": _round(humidity),
        "pressure": classify_pressure(current.get("pressure_msl")),
        "wind_kmh": _kmh(current.get("wind_speed_10m")),
        "cloud_cover": current.get("cloud_cover"),
        "condition": condition,
        "emoji": emoji,
        "wet_bulb": wet_bulb,
        "wet_bulb_risk": wet_bulb_risk(wet_bulb),
    }


def build_daily(data):
    daily = data.get("daily", {})
    hourly_by_day = _group_hourly_by_day(data.get("hourly", {}))

    def col(name, i):
        series = daily.get(name) or []
        return series[i] if i < len(series) else None

    forecast = []
    previous_pressure = None
    for i, date_str in enumerate(daily.get("time", [])):
        hours = hourly_by_day.get(date_str, [])
        pressure_mean = _mean(h.get("pressure_msl") for h in hours)
        wet_bulbs = [calculate_wet_bulb(h.get("temperature_2m"), h.get("relative_humidity_2m"))
                     for h in hours]
        wet_bulbs = [w for w in wet_bulbs if w is not None]
        wet_bulb_max = max(wet_bulbs) if wet_bulbs else None
        condition, emoji = wmo.describe(col("weather_code", i))

        forecast.append({
            "date": datetime.date.fromisoformat(date_str),
            "condition": condition,
            "emoji": emoji,
            "temp_max": _round(col("temperature_2m_max", i), 1),
            "temp_min": _round(col("temperature_2m_min", i), 1),
            "humidity_mean": _round(col("relative_humidity_2m_mean", i)),
            "humidity_min": _round(col("relative_humidity_2m_min", i)),
            "humidity_max": _round(col("relative_humidity_2m_max", i)),
            "precipitation": _round(col("precipitation_sum", i), 1),
            "wind_max_kmh": _kmh(col("wind_speed_10m_max", i)),
            "pressure": classify_pressure(pressure_mean, previous_pressure),
            "wet_bulb_max": wet_bulb_max,
            "wet_bulb_risk": wet_bulb_risk(wet_bulb_max),
        })
        previous_pressure = pressure_mean
    return forecast


def get_weather(latitude, longitude, timezone="auto"):
    """Condições atuais + previsão diária para as coordenadas informadas."""
    raw = met_norway.fetch_raw(round(latitude, 4), round(longitude, 4))
    data = met_norway.parse(raw, timezone, FORECAST_DAYS)
    return {
        "current": build_current(data),
        "daily": build_daily(data),
        "timezone": data.get("timezone"),
    }
