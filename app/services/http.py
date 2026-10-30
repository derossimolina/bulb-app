"""Cliente HTTP compartilhado e cache simples em memória."""
import threading
import time
from functools import wraps

import requests

USER_AGENT = "WetBulbApp/2.0 (+https://derossi.dev)"
DEFAULT_TIMEOUT = 15
RETRY_STATUSES = {429, 502, 503, 504}
MAX_RETRY_WAIT = 2  # segundos; esperas maiores ficam a cargo da fonte reserva

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})


class ServiceError(Exception):
    """Falha ao consultar um serviço externo. `status` é o código HTTP, quando houver."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _retry_wait(response):
    try:
        return min(float(response.headers.get("Retry-After", 1)), MAX_RETRY_WAIT)
    except ValueError:
        return 1


def get_json(url, params=None, timeout=DEFAULT_TIMEOUT, retries=1):
    """GET que devolve JSON. Repete `retries` vez(es) em 429/5xx transitórios."""
    for attempt in range(retries + 1):
        try:
            response = _session.get(url, params=params, timeout=timeout)
            if response.status_code in RETRY_STATUSES and attempt < retries:
                time.sleep(_retry_wait(response))
                continue
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            body = (exc.response.text or "")[:200] if exc.response is not None else ""
            status = exc.response.status_code if exc.response is not None else None
            raise ServiceError(f"{url}: {exc} {body}".strip(), status=status) from exc
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
