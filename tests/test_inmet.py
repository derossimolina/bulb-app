import json

from app.services import inmet

SQUARE = json.dumps({"type": "Polygon", "coordinates": [[[-52, -31], [-50, -31], [-50, -29], [-52, -29], [-52, -31]]]})


def _alert(geocodes, poligono=SQUARE, severidade="Perigo"):
    return {
        "id_aviso": 1, "descricao": "Tempestade", "severidade": severidade, "aviso_cor": "#F96602",
        "inicio": "2026-10-15 00:00", "fim": "2026-10-15 23:59", "geocodes": geocodes, "poligono": poligono,
        "riscos": ["Chuva forte"], "instrucoes": ["Evite áreas alagadas"],
    }


def test_find_ibge_code_handles_accents_and_state_formats():
    assert inmet.find_ibge_code("Porto Alegre", "Rio Grande do Sul") == "4314902"
    assert inmet.find_ibge_code("Sao Paulo", "SP") == "3550308"
    assert inmet.find_ibge_code("Florianópolis", "Santa Catarina") == "4205407"
    assert inmet.find_ibge_code("Atlantis", "Rio Grande do Sul") is None


def test_point_in_geojson():
    assert inmet.point_in_geojson(-51.2, -30.0, SQUARE)
    assert not inmet.point_in_geojson(-40, -20, SQUARE)
    assert not inmet.point_in_geojson(-51.2, -30.0, "invalid")


def test_alerts_matched_by_ibge_code(monkeypatch):
    monkeypatch.setattr(inmet, "_active_alerts", lambda: [
        ("today", _alert("4314902,4300000")),
        ("future", _alert("9999999", poligono=SQUARE)),  # polígono cobre, mas código não → ignorado
    ])
    result = inmet.get_alerts_for_city("Porto Alegre", "Rio Grande do Sul", -30.03, -51.23)
    assert result["ibge_code"] == "4314902"
    assert len(result["alerts"]) == 1
    alert = result["alerts"][0]
    assert alert["css"] == "orange" and alert["risks"] == ["Chuva forte"]


def test_alerts_polygon_fallback(monkeypatch):
    monkeypatch.setattr(inmet, "_active_alerts", lambda: [("today", _alert("9999999"))])
    result = inmet.get_alerts_for_city("Unknown Town", "Rio Grande do Sul", -30.0, -51.2)
    assert result["ibge_code"] is None
    assert len(result["alerts"]) == 1


def test_alerts_service_down(monkeypatch):
    def boom():
        raise inmet.ServiceError("down")
    monkeypatch.setattr(inmet, "_active_alerts", boom)
    result = inmet.get_alerts_for_city("Porto Alegre", "Rio Grande do Sul", -30.03, -51.23)
    assert result["available"] is False and result["alerts"] == []


def test_alerts_by_date_spans_days_and_dedupes():
    import datetime
    alerts = [
        {"id": 1, "event": "Tempestade", "severity_rank": 1, "start": "2026-10-30 12:00", "end": "2026-11-01 08:00"},
        {"id": 1, "event": "Tempestade", "severity_rank": 1, "start": "2026-10-31 00:00", "end": "2026-10-31 23:59"},
        {"id": 2, "event": "Chuva", "severity_rank": 2, "start": "2026-10-31 00:00", "end": "2026-10-31 23:59"},
    ]
    days = inmet.alerts_by_date(alerts)
    d = datetime.date
    assert [a["id"] for a in days[d(2026, 10, 30)]] == [1]
    assert [a["id"] for a in days[d(2026, 10, 31)]] == [2, 1]   # mais severo primeiro, sem repetir
    assert [a["id"] for a in days[d(2026, 11, 1)]] == [1]
