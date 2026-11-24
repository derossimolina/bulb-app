"""
Códigos de tempo WMO → descrição e ícone (os símbolos do MET Norway são convertidos para eles).

O ícone é o nome de um ícone Lucide do sprite `static/icons.svg` (design system, seção 2.6), sem
emoji na interface (SPEC.md REQ-DS-06).
"""
from flask_babel import lazy_gettext as _l

WMO_CODES = {
    0: (_l("Clear sky"), "sun"),
    1: (_l("Mainly clear"), "sun"),
    2: (_l("Partly cloudy"), "cloud-sun"),
    3: (_l("Overcast"), "cloud"),
    45: (_l("Fog"), "cloud-fog"),
    48: (_l("Depositing rime fog"), "cloud-fog"),
    51: (_l("Light drizzle"), "cloud-drizzle"),
    53: (_l("Moderate drizzle"), "cloud-drizzle"),
    55: (_l("Dense drizzle"), "cloud-drizzle"),
    56: (_l("Light freezing drizzle"), "cloud-drizzle"),
    57: (_l("Dense freezing drizzle"), "cloud-drizzle"),
    61: (_l("Slight rain"), "cloud-rain"),
    63: (_l("Moderate rain"), "cloud-rain"),
    65: (_l("Heavy rain"), "cloud-rain-wind"),
    66: (_l("Light freezing rain"), "cloud-rain"),
    67: (_l("Heavy freezing rain"), "cloud-rain-wind"),
    71: (_l("Slight snowfall"), "snowflake"),
    73: (_l("Moderate snowfall"), "snowflake"),
    75: (_l("Heavy snowfall"), "snowflake"),
    77: (_l("Snow grains"), "snowflake"),
    80: (_l("Slight rain showers"), "cloud-sun-rain"),
    81: (_l("Moderate rain showers"), "cloud-rain-wind"),
    82: (_l("Violent rain showers"), "cloud-rain-wind"),
    85: (_l("Slight snow showers"), "snowflake"),
    86: (_l("Heavy snow showers"), "snowflake"),
    95: (_l("Thunderstorm"), "cloud-lightning"),
    96: (_l("Thunderstorm with slight hail"), "cloud-lightning"),
    99: (_l("Thunderstorm with heavy hail"), "cloud-lightning"),
}
DEFAULT_ICON = "thermometer"


def describe(code):
    """Retorna (descrição, ícone) para um código WMO."""
    if code is None:
        return ("", DEFAULT_ICON)
    return WMO_CODES.get(int(code), ("", DEFAULT_ICON))
