"""Cliente HTTP compartilhado e cache simples em memória."""
import threading
import time
from functools import wraps

import requests

USER_AGENT = "WetBulbApp/2.0 (+https://derossi.dev)"
DEFAULT_TIMEOUT = 15

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})


class ServiceError(Exception):
    """Falha ao consultar um serviço externo."""


def get_json(url, params=None, timeout=DEFAULT_TIMEOUT):
    try:
        response = _session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ServiceError(f"{url}: {exc}") from exc


def ttl_cache(seconds):
    """Memoriza o resultado de uma função por `seconds` segundos (thread-safe)."""
    def decorator(func):
        store = {}
        lock = threading.Lock()

        @wraps(func)
        def wrapper(*args):
            now = time.monotonic()
            with lock:
                hit = store.get(args)
                if hit and now - hit[0] < seconds:
                    return hit[1]
            value = func(*args)
            with lock:
                store[args] = (now, value)
            return value

        wrapper.cache_clear = store.clear
        return wrapper
    return decorator
