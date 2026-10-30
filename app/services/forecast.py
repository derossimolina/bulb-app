"""
Condições atuais e previsão de 7 dias via Open-Meteo.

O Open-Meteo combina automaticamente os melhores modelos numéricos disponíveis
para cada local (ECMWF IFS, DWD ICON, NOAA GFS, entre outros), com resolução de
até 1–11 km e atualização horária. Não requer chave de API.

O limite gratuito do Open-Meteo é por IP. No plano Free do Render o IP de saída é
compartilhado, então ele pode responder 429 mesmo com pouco uso desta aplicação.
Nesse caso (ou em qualquer outra falha) os dados vêm do MET Norway; veja met_norway.py.
"""
import datetime
import logging
import time
from collections import defaultdict

from ..meteo import wmo
from ..meteo.indices import bulk_shear, classify_pressure, tornado_potential_day
from ..meteo.wetbulb import calculate_wet_bulb, wet_bulb_risk
from . import met_norway
from .http import ServiceError, get_json, ttl_cache

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 7
MS_TO_KMH = 3.6
# Depois de um 429, vai direto para a fonte reserva por este tempo (segundos)
RATE_LIMIT_PAUSE = 120

log = logging.getLogger(__name__)
_open_meteo_paused_until = 0.0

CURRENT_VARS = [
    "temperature_2m", "relative_humidity_2m", "apparent_temperature", "dew_point_2m",
    "pressure_msl", "weather_code", "wind_speed_10m", "wind_gusts_10m",
    "precipitation", "cloud_cover", "is_day",
]
DAILY_VARS = [
    "weather_code", "temperature_2m_max", "temperature_2m_min",
    "relative_humidity_2m_mean", "relative_humidity_2m_min", "relative_humidity_2m_max",
    "precipitation_sum", "precipitation_probability_max", "wind_gusts_10m_max", "uv_index_max",
]
HOURLY_VARS = [
    "temperature_2m", "relative_humidity_2m", "pressure_msl", "cape", "lifted_index",
    "wind_speed_10m", "wind_direction_10m",
    "wind_speed_850hPa", "wind_direction_850hPa",
    "wind_speed_500hPa", "wind_direction_500hPa",
]


@ttl_cache(seconds=15 * 60)
def fetch_raw(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "forecast_days": FORECAST_DAYS,
        "wind_speed_unit": "ms",
        "current": ",".join(CURRENT_VARS),
        "daily": ",".join(DAILY_VARS),
        "hourly": ",".join(HOURLY_VARS),
    }
    return get_json(FORECAST_URL, params)


def _round(value, digits=0):
    if value is None:
        return None
    return round(value, digits) if digits else int(round(value))


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _group_hourly_by_day(hourly):
    """Agrupa as séries horárias por data local (YYYY-MM-DD)."""
    days = defaultdict(list)
    times = hourly.get("time", [])
    for i, timestamp in enumerate(times):
        row = {key: (series[i] if i < len(series) else None)
               for key, series in hourly.items() if key != "time"}
        row["deep_shear"] = bulk_shear(row.get("wind_speed_10m"), row.get("wind_direction_10m"),
                                       row.get("wind_speed_500hPa"), row.get("wind_direction_500hPa"))
        row["low_shear"] = bulk_shear(row.get("wind_speed_10m"), row.get("wind_direction_10m"),
                                      row.get("wind_speed_850hPa"), row.get("wind_direction_850hPa"))
        days[timestamp[:10]].append(row)
    return days


def build_current(raw):
    current = raw.get("current", {})
    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    wet_bulb = calculate_wet_bulb(temp, humidity)
    condition, emoji = wmo.describe(current.get("weather_code"))
    gusts = current.get("wind_gusts_10m")
    wind = current.get("wind_speed_10m")
    return {
        "time": current.get("time"),
        "temperature": _round(temp, 1),
        "apparent_temperature": _round(current.get("apparent_temperature"), 1),
        "dew_point": _round(current.get("dew_point_2m"), 1),
        "humidity": _round(humidity),
        "pressure": classify_pressure(current.get("pressure_msl")),
        "wind_kmh": _round(wind * MS_TO_KMH) if wind is not None else None,
        "gusts_kmh": _round(gusts * MS_TO_KMH) if gusts is not None else None,
        "cloud_cover": current.get("cloud_cover"),
        "condition": condition,
        "emoji": emoji,
        "wet_bulb": wet_bulb,
        "wet_bulb_risk": wet_bulb_risk(wet_bulb),
    }


def build_daily(raw):
    daily = raw.get("daily", {})
    hourly_by_day = _group_hourly_by_day(raw.get("hourly", {}))

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
        gusts = col("wind_gusts_10m_max", i)

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
            "precipitation_probability": col("precipitation_probability_max", i),
            "gusts_kmh": _round(gusts * MS_TO_KMH) if gusts is not None else None,
            "uv_index": _round(col("uv_index_max", i), 1),
            "pressure": classify_pressure(pressure_mean, previous_pressure),
            "tornado": tornado_potential_day(hours),
            "wet_bulb_max": wet_bulb_max,
            "wet_bulb_risk": wet_bulb_risk(wet_bulb_max),
        })
        previous_pressure = pressure_mean
    return forecast


def _fetch(latitude, longitude, timezone):
    """Dados no formato do Open-Meteo e a fonte usada ("open_meteo" ou "met_norway")."""
    global _open_meteo_paused_until
    if time.monotonic() >= _open_meteo_paused_until:
        try:
            return fetch_raw(latitude, longitude), "open_meteo"
        except ServiceError as exc:
            log.warning("Open-Meteo indisponível, usando MET Norway: %s", exc)
            if exc.status == 429:
                _open_meteo_paused_until = time.monotonic() + RATE_LIMIT_PAUSE
    raw = met_norway.fetch_raw(latitude, longitude)
    return met_norway.to_open_meteo(raw, timezone, FORECAST_DAYS), "met_norway"


def get_weather(latitude, longitude, timezone="auto"):
    """Condições atuais + previsão diária para as coordenadas informadas."""
    raw, source = _fetch(round(latitude, 4), round(longitude, 4), timezone)
    return {
        "current": build_current(raw),
        "daily": build_daily(raw),
        "timezone": raw.get("timezone"),
        "source": source,
    }
