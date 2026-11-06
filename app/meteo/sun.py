"""Elevação do sol (algoritmo simplificado da NOAA, erro ~1° — suficiente para "dia ou noite")."""
import datetime
import math


def solar_elevation(latitude, longitude, when_utc):
    """Ângulo do sol acima do horizonte, em graus, no instante `when_utc` (datetime com fuso)."""
    when = when_utc.astimezone(datetime.timezone.utc)
    day_of_year = when.timetuple().tm_yday
    hours = when.hour + when.minute / 60 + when.second / 3600
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + (hours - 12) / 24)

    equation_of_time = 229.18 * (
        0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma)
    )
    declination = (
        0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
    )
    true_solar_minutes = hours * 60 + equation_of_time + 4 * longitude
    hour_angle = math.radians(true_solar_minutes / 4 - 180)
    lat = math.radians(latitude)

    cos_zenith = (math.sin(lat) * math.sin(declination)
                  + math.cos(lat) * math.cos(declination) * math.cos(hour_angle))
    return 90 - math.degrees(math.acos(max(-1.0, min(1.0, cos_zenith))))


def is_sun_up(latitude, longitude, when_utc):
    return solar_elevation(latitude, longitude, when_utc) > 0
