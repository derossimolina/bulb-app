"""
Previsão do MET Norway (Instituto Meteorológico da Noruega): fonte única de dados.

API gratuita e global, sem chave; exige User-Agent identificável e cache das
respostas. Licença dos dados: CC BY 4.0.
https://api.met.no/weatherapi/locationforecast/2.0/documentation

A série vem em UTC, de hora em hora nos primeiros ~2,5 dias e de 6 em 6 horas
depois. `parse` converte para horário local e agrega por dia. Fora da
Escandinávia o MET Norway não traz rajadas nem probabilidade de chuva, por isso
esses dados não são usados.
"""
import datetime
from collections import defaultdict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .http import get_json, ttl_cache

FORECAST_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"

# symbol_code do MET Norway (sem o sufixo _day/_night/_polartwilight) → código WMO
SYMBOL_TO_WMO = {
    "clearsky": 0, "fair": 1, "partlycloudy": 2, "cloudy": 3, "fog": 45,
    "lightrain": 61, "rain": 63, "heavyrain": 65,
    "lightrainshowers": 80, "rainshowers": 81, "heavyrainshowers": 82,
    "lightsleet": 66, "sleet": 67, "heavysleet": 67,
    "lightsleetshowers": 85, "sleetshowers": 85, "heavysleetshowers": 86,
    "lightsnow": 71, "snow": 73, "heavysnow": 75,
    "lightsnowshowers": 85, "snowshowers": 85, "heavysnowshowers": 86,
}


@ttl_cache(seconds=30 * 60)
def fetch_raw(latitude, longitude):
    # A API aceita no máximo 4 casas decimais
    return get_json(FORECAST_URL, {"lat": round(latitude, 4), "lon": round(longitude, 4)})


def symbol_to_wmo(symbol):
    if not symbol:
        return None
    base = symbol.split("_")[0]
    if "thunder" in base:
        return 95
    return SYMBOL_TO_WMO.get(base, 3)


def _zone(name):
    try:
        return ZoneInfo(name) if name and name != "auto" else datetime.timezone.utc
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.timezone.utc


def _values(rows, key):
    return [r[key] for r in rows if r.get(key) is not None]


def _mean(values):
    return sum(values) / len(values) if values else None


def parse(raw, timezone, days=7):
    """Converte a resposta do MET Norway em séries {current, daily, hourly} no horário local."""
    tz = _zone(timezone)
    rows = []
    for item in raw.get("properties", {}).get("timeseries", []):
        data = item.get("data", {})
        instant = data.get("instant", {}).get("details", {})
        # Precipitação e símbolo do período seguinte; 1 h no início da série, 6 h depois
        period = data.get("next_1_hours") or data.get("next_6_hours") or {}
        period_details = period.get("details", {})
        local = datetime.datetime.fromisoformat(item["time"].replace("Z", "+00:00")).astimezone(tz)
        rows.append({
            "local": local,
            "temperature_2m": instant.get("air_temperature"),
            "relative_humidity_2m": instant.get("relative_humidity"),
            "pressure_msl": instant.get("air_pressure_at_sea_level"),
            "dew_point_2m": instant.get("dew_point_temperature"),
            "apparent_temperature": instant.get("apparent_air_temperature"),
            "wind_speed_10m": instant.get("wind_speed"),
            "wind_direction_10m": instant.get("wind_from_direction"),
            "cloud_cover": instant.get("cloud_area_fraction"),
            "weather_code": symbol_to_wmo(period.get("summary", {}).get("symbol_code")),
            "precipitation": period_details.get("precipitation_amount"),
            "temp_max": period_details.get("air_temperature_max"),
            "temp_min": period_details.get("air_temperature_min"),
        })
    if not rows:
        return {"timezone": str(tz), "current": {}, "daily": {"time": []}, "hourly": {"time": []}}

    first = rows[0]
    current = {key: first[key] for key in (
        "temperature_2m", "relative_humidity_2m", "apparent_temperature", "dew_point_2m",
        "pressure_msl", "weather_code", "wind_speed_10m", "precipitation", "cloud_cover",
    )}
    current["time"] = first["local"].strftime("%Y-%m-%dT%H:%M")

    hourly_keys = ("temperature_2m", "relative_humidity_2m", "pressure_msl", "wind_speed_10m", "wind_direction_10m")
    hourly = {"time": [r["local"].strftime("%Y-%m-%dT%H:%M") for r in rows]}
    for key in hourly_keys:
        hourly[key] = [r[key] for r in rows]

    by_day = defaultdict(list)
    for r in rows:
        by_day[r["local"].date()].append(r)
    daily = defaultdict(list)
    for date in sorted(by_day)[:days]:
        day = by_day[date]
        temps = _values(day, "temperature_2m")
        humidity = _values(day, "relative_humidity_2m")
        codes = _values(day, "weather_code")
        precipitation = _values(day, "precipitation")
        wind = _values(day, "wind_speed_10m")
        daily["time"].append(date.isoformat())
        daily["temperature_2m_max"].append(max(temps + _values(day, "temp_max"), default=None))
        daily["temperature_2m_min"].append(min(temps + _values(day, "temp_min"), default=None))
        daily["relative_humidity_2m_mean"].append(_mean(humidity))
        daily["relative_humidity_2m_min"].append(min(humidity, default=None))
        daily["relative_humidity_2m_max"].append(max(humidity, default=None))
        daily["weather_code"].append(max(codes, default=None))  # condição mais severa do dia
        daily["precipitation_sum"].append(round(sum(precipitation), 1) if precipitation else None)
        daily["wind_speed_10m_max"].append(max(wind, default=None))

    return {"timezone": str(tz), "current": current, "daily": dict(daily), "hourly": hourly}
