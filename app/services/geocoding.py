"""Busca de cidades pela API de geocodificação do Open-Meteo (GeoNames)."""
from .http import get_json, ttl_cache
from .text import normalize

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

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
    if result.get("country_code") == "BR" and region.upper() in BR_STATES:
        if normalize(result.get("admin1")) == normalize(BR_STATES[region.upper()]):
            return True
    for candidate in (result.get("country_code"), result.get("country"), result.get("admin1"), result.get("admin2")):
        value = normalize(candidate)
        if value and (value == wanted or (len(wanted) > 2 and value.startswith(wanted))):
            return True
    return False


def _search(name, language):
    params = {"name": name, "count": 50, "language": language, "format": "json"}
    return get_json(GEOCODING_URL, params).get("results") or []


def _pick_best(results, name):
    """
    Prefere cidades (feature_code PPL*) com o nome exato e maior população;
    sem isso, mantém a ordem de relevância da API.
    """
    cities = [r for r in results if str(r.get("feature_code", "")).startswith("PPL")] or results
    exact = [r for r in cities if normalize(r.get("name")) == normalize(name)]
    if exact:
        return max(exact, key=lambda r: r.get("population") or 0)
    return cities[0]


@ttl_cache(seconds=24 * 3600)
def find_city(query, language="en"):
    """Retorna a localidade mais relevante para o texto informado."""
    name, region = parse_query(query)
    if len(name) < 2:
        raise CityNotFound(query)

    results = _search(name, language)
    if region:
        matching = [r for r in results if _matches_region(r, region)]
        if not matching and language != "en":
            # nomes de estados/países vêm traduzidos; tenta também em inglês
            matching = [r for r in _search(name, "en") if _matches_region(r, region)]
        results = matching
    if not results:
        raise CityNotFound(query)

    best = _pick_best(results, name)
    return {
        "name": best["name"],
        "latitude": best["latitude"],
        "longitude": best["longitude"],
        "country": best.get("country", ""),
        "country_code": best.get("country_code", ""),
        "state": best.get("admin1", ""),
        "timezone": best.get("timezone", "auto"),
        "elevation": best.get("elevation"),
    }
