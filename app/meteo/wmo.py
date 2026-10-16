"""Códigos de tempo WMO (usados pelo Open-Meteo) → descrição e emoji."""
from flask_babel import lazy_gettext as _l

WMO_CODES = {
    0: (_l("Clear sky"), "☀️"),
    1: (_l("Mainly clear"), "🌤️"),
    2: (_l("Partly cloudy"), "⛅"),
    3: (_l("Overcast"), "☁️"),
    45: (_l("Fog"), "🌫️"),
    48: (_l("Depositing rime fog"), "🌫️"),
    51: (_l("Light drizzle"), "🌦️"),
    53: (_l("Moderate drizzle"), "🌦️"),
    55: (_l("Dense drizzle"), "🌧️"),
    56: (_l("Light freezing drizzle"), "🌧️"),
    57: (_l("Dense freezing drizzle"), "🌧️"),
    61: (_l("Slight rain"), "🌦️"),
    63: (_l("Moderate rain"), "🌧️"),
    65: (_l("Heavy rain"), "🌧️"),
    66: (_l("Light freezing rain"), "🌧️"),
    67: (_l("Heavy freezing rain"), "🌧️"),
    71: (_l("Slight snowfall"), "🌨️"),
    73: (_l("Moderate snowfall"), "🌨️"),
    75: (_l("Heavy snowfall"), "❄️"),
    77: (_l("Snow grains"), "❄️"),
    80: (_l("Slight rain showers"), "🌦️"),
    81: (_l("Moderate rain showers"), "🌧️"),
    82: (_l("Violent rain showers"), "⛈️"),
    85: (_l("Slight snow showers"), "🌨️"),
    86: (_l("Heavy snow showers"), "❄️"),
    95: (_l("Thunderstorm"), "⛈️"),
    96: (_l("Thunderstorm with slight hail"), "⛈️"),
    99: (_l("Thunderstorm with heavy hail"), "⛈️"),
}


def describe(code):
    """Retorna (descrição, emoji) para um código WMO."""
    if code is None:
        return ("", "🌡️")
    return WMO_CODES.get(int(code), ("", "🌡️"))
