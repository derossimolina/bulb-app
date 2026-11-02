"""
Busca de cidades pelo Nominatim (OpenStreetMap), com a geocodificação do
Open-Meteo como reserva.

Política de uso do Nominatim: no máximo 1 requisição por segundo, User-Agent
identificável e cache dos resultados (feito aqui por 24 h).
https://operations.osmfoundation.org/policies/nominatim/
O Nominatim bloqueia IPs muito usados, e no plano Free do Render o IP de saída é
compartilhado: em 02/11/2026 ele respondeu 429 a todas as buscas de produção.
Quando isso acontece, a busca usa o Open-Meteo e o Nominatim fica em pausa.
O fuso horário é obtido pelas coordenadas com o tzfpy.
"""
import logging
import time

from tzfpy import get_tz

from .http import ServiceError, get_json, ttl_cache
from .text import normalize

SEARCH_URL = "https://nominatim.openstreetmap.org/search"
FALLBACK_URL = "https://geocoding-api.open-meteo.com/v1/search"
SETTLEMENT_TYPES = ("city", "town", "village", "municipality")
# Depois de uma recusa do Nominatim, usa só a reserva por este tempo (segundos)
NOMINATIM_PAUSE = 10 * 60

log = logging.getLogger(__name__)
_nominatim_paused_until = 0.0

# Siglas das UFs brasileiras → nome do estado (para buscas como "Santa Maria, RS")
BR_STATES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará",
    "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}


class CityNotFound(Exception):
    pass


def parse_query(query):
    """Separa 'Cidade, Região' em (nome, região). A região pode ser país, estado ou UF."""
    name, _, region = (query or "").partition(",")
    return name.strip(), region.strip() or None


def _matches_region(result, region):
    """Verifica se o resultado pertence à região informada (código/nome de país, estado ou UF)."""
    wanted = normalize(region)
    code = region.upper()
    if result.get("country_code") == "BR" and code in BR_STATES:
        if result.get("state_code") == f"BR-{code}" or normalize(result.get("admin1")) == normalize(BR_STATES[code]):
            return True
    for candidate in (result.get("country_code"), result.get("country"), result.get("admin1"), result.get("admin2")):
        value = normalize(candidate)
        if value and (value == wanted or (len(wanted) > 2 and value.startswith(wanted))):
            return True
    return False


def _from_nominatim(item):
    address = item.get("address", {})
    return {
        "name": item.get("name") or address.get("city") or address.get("town") or address.get("village", ""),
        "latitude": float(item["lat"]),
        "longitude": float(item["lon"]),
        "country": address.get("country", ""),
        "country_code": address.get("country_code", "").upper(),
        "admin1": address.get("state", ""),
        "admin2": address.get("county") or address.get("state_district", ""),
        "state_code": address.get("ISO3166-2-lvl4", ""),
        "type": item.get("addresstype", ""),
    }


def _from_open_meteo(item):
    return {
        "name": item.get("name", ""),
        "latitude": item["latitude"],
        "longitude": item["longitude"],
        "country": item.get("country", ""),
        "country_code": item.get("country_code", "").upper(),
        "admin1": item.get("admin1", ""),
        "admin2": item.get("admin2", ""),
        "state_code": "",
        "type": "city" if str(item.get("feature_code", "")).startswith("PPL") else "",
        "population": item.get("population"),
    }


def _search_nominatim(query, language):
    params = {
        "q": query, "format": "jsonv2", "addressdetails": 1, "limit": 40,
        "featureType": "settlement", "accept-language": language,
    }
    return [_from_nominatim(item) for item in get_json(SEARCH_URL, params)]


def _search_open_meteo(query, language):
    params = {"name": query, "count": 50, "language": language, "format": "json"}
    return [_from_open_meteo(item) for item in get_json(FALLBACK_URL, params).get("results") or []]


def _search(query, language):
    """Nominatim; se ele recusar ou falhar, geocodificação do Open-Meteo."""
    global _nominatim_paused_until
    if time.monotonic() >= _nominatim_paused_until:
        try:
            return _search_nominatim(query, language)
        except ServiceError as exc:
            log.warning("Nominatim indisponível, usando o Open-Meteo: %s", exc)
            _nominatim_paused_until = time.monotonic() + NOMINATIM_PAUSE
    # O Open-Meteo busca só pelo nome; a região ("Cidade, UF") é filtrada depois
    return _search_open_meteo(query.partition(",")[0].strip(), language)


def _pick_best(results, name):
    """
    Prefere municípios/cidades com o nome exato. O Nominatim já ordena por
    importância (o primeiro é o mais relevante); na reserva do Open-Meteo, que
    traz população, vence a mais populosa.
    """
    settlements = [r for r in results if r["type"] in SETTLEMENT_TYPES] or results
    exact = [r for r in settlements if normalize(r["name"]) == normalize(name)]
    if any(r.get("population") for r in exact):
        return max(exact, key=lambda r: r.get("population") or 0)
    return (exact or settlements)[0]


@ttl_cache(seconds=24 * 3600)
def find_city(query, language="en"):
    """Retorna a localidade mais relevante para o texto informado."""
    name, region = parse_query(query)
    if len(name) < 2:
        raise CityNotFound(query)

    results = _search(name, language)
    if region:
        matching = [r for r in results if _matches_region(r, region)]
        if not matching:
            # Cidades pequenas podem não aparecer entre os 40 primeiros: busca com a região no texto
            matching = [r for r in _search(f"{name}, {region}", language) if _matches_region(r, region)]
        results = matching
    if not results:
        raise CityNotFound(query)

    best = _pick_best(results, name)
    return {
        "name": best["name"],
        "latitude": best["latitude"],
        "longitude": best["longitude"],
        "country": best["country"],
        "country_code": best["country_code"],
        "state": best["admin1"],
        "timezone": get_tz(best["longitude"], best["latitude"]) or "UTC",
    }
