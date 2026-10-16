"""
Avisos meteorológicos oficiais do INMET (Instituto Nacional de Meteorologia).

Fonte: API pública https://apiprevmet3.inmet.gov.br/avisos/ativos, a mesma usada
pelo portal https://avisos.inmet.gov.br. Cada aviso lista os municípios afetados
pelo código IBGE (`geocodes`) e o polígono da área de risco (`poligono`).
O código IBGE da cidade vem da tabela de municípios do IBGE em app/data
(atualizável com scripts/update_ibge_municipios.py). Se a cidade não for
encontrada na tabela, usa-se o polígono do aviso para verificar a localização.
"""
import json
import logging
from functools import lru_cache
from pathlib import Path

from .http import ServiceError, get_json, ttl_cache
from .text import normalize as _normalize

INMET_ALERTS_URL = "https://apiprevmet3.inmet.gov.br/avisos/ativos"
MUNICIPALITIES_FILE = Path(__file__).resolve().parent.parent / "data" / "municipios_ibge.json"
INMET_PORTAL_URL = "https://avisos.inmet.gov.br"

log = logging.getLogger(__name__)

# Escala de severidade do INMET (cores oficiais)
SEVERITY = {
    "Perigo Potencial": {"rank": 1, "css": "yellow"},
    "Perigo": {"rank": 2, "css": "orange"},
    "Grande Perigo": {"rank": 3, "css": "red"},
}


@lru_cache(maxsize=1)
def _municipality_index():
    """Índice {(nome normalizado, estado normalizado): código IBGE}."""
    data = json.loads(MUNICIPALITIES_FILE.read_text(encoding="utf-8"))
    index = {}
    for uf, municipalities in data["municipalities"].items():
        state_keys = (_normalize(uf), _normalize(data["states"][uf]))
        for name, code in municipalities.items():
            for state_key in state_keys:
                index[(_normalize(name), state_key)] = str(code)
    return index


def find_ibge_code(city_name, state):
    """Código IBGE de 7 dígitos do município, ou None se não encontrado."""
    return _municipality_index().get((_normalize(city_name), _normalize(state)))


@ttl_cache(seconds=10 * 60)
def _active_alerts():
    data = get_json(INMET_ALERTS_URL, timeout=25)
    return [("today", a) for a in data.get("hoje", [])] + [("future", a) for a in data.get("futuro", [])]


def _point_in_ring(lon, lat, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def point_in_geojson(lon, lat, geometry):
    """Verifica se o ponto está dentro de um Polygon/MultiPolygon GeoJSON."""
    if isinstance(geometry, str):
        try:
            geometry = json.loads(geometry)
        except ValueError:
            return False
    if not isinstance(geometry, dict):
        return False
    kind = geometry.get("type")
    polygons = ([geometry.get("coordinates", [])] if kind == "Polygon"
                else geometry.get("coordinates", []) if kind == "MultiPolygon" else [])
    for polygon in polygons:
        if polygon and _point_in_ring(lon, lat, polygon[0]) and not any(
            _point_in_ring(lon, lat, hole) for hole in polygon[1:]
        ):
            return True
    return False


def _as_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def _format_alert(period, alert):
    severity = alert.get("severidade", "")
    meta = SEVERITY.get(severity, {"rank": 0, "css": "grey"})
    return {
        "id": alert.get("id_aviso"),
        "period": period,
        "event": alert.get("descricao", ""),
        "severity": severity,
        "severity_rank": meta["rank"],
        "css": meta["css"],
        "color": alert.get("aviso_cor"),
        "start": alert.get("inicio"),
        "end": alert.get("fim"),
        "risks": _as_list(alert.get("riscos")),
        "instructions": _as_list(alert.get("instrucoes")),
        "icon": alert.get("icone") if str(alert.get("icone", "")).startswith("data:image/") else None,
    }


def get_alerts_for_city(city_name, state, latitude, longitude):
    """
    Avisos ativos (hoje e próximos dias) que afetam o município.

    Retorna {"alerts": [...], "ibge_code": str|None, "available": bool}.
    """
    ibge_code = find_ibge_code(city_name, state)
    try:
        active = _active_alerts()
    except ServiceError as exc:
        log.warning("INMET indisponível: %s", exc)
        return {"alerts": [], "ibge_code": ibge_code, "available": False}

    matches = []
    for period, alert in active:
        geocodes = {g.strip() for g in str(alert.get("geocodes", "")).split(",")}
        if ibge_code and ibge_code in geocodes:
            matches.append(_format_alert(period, alert))
        elif not ibge_code and point_in_geojson(longitude, latitude, alert.get("poligono")):
            matches.append(_format_alert(period, alert))

    matches.sort(key=lambda a: (a["start"] or "", -a["severity_rank"]))
    return {"alerts": matches, "ibge_code": ibge_code, "available": True, "portal": INMET_PORTAL_URL}
