"""
Paridade entre o motor de risco em JavaScript (app/static/risk.js) e o em Python
(SPEC.md 4.6 e NFR-04): mesmos casos, mesmo resultado e mesmas frases.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app import create_app
from app.meteo import risk

ROOT = Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / "spec" / "risk-cases.json").read_text(encoding="utf-8"))["cases"]
NODE = shutil.which("node")

# Casos extras com rótulos de horário, para comparar também as frases
EXTRA = [
    {"id": 101, "hours": [
        {"label": "14h", "temp": 33, "tw": 32.5, "thunder": True},
        {"label": "15h", "temp": 37, "tw": 31.2, "cloud": 10, "sun_up": True, "thunder": True, "wind_kmh": 72.4,
         "alerts": [{"event": "Tempestade", "severity": "Perigo Potencial"}, {"event": "Tempestade", "severity": "Perigo"}]},
        {"label": "16h", "temp": 39.5, "tw": 29, "thunder": True,
         "alerts": [{"event": "Vendaval", "severity": "Grande Perigo"}]},
        {"label": "17h", "temp": 30, "tw": 25, "tornado": "high"},
    ]},
    {"id": 102, "hours": [{"label": "9h", "temp": 20, "tw": 15, "alerts": [{"event": "Vendaval", "severity": "Perigo"}]}]},
]

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js não instalado")


def _run_js(cases, strings):
    proc = subprocess.run([NODE, str(ROOT / "tests" / "js" / "run_cases.js")],
                          input=json.dumps({"cases": cases, "strings": strings}),
                          capture_output=True, text=True, encoding="utf-8", check=True)
    return {r["id"]: r for r in json.loads(proc.stdout)}


@pytest.fixture(scope="module")
def js_results():
    with create_app().test_request_context("/?lang=en"):
        strings = risk.client_strings()
    return _run_js(CASES + EXTRA, strings)


@pytest.mark.parametrize("case", CASES + EXTRA, ids=lambda c: str(c["id"]))
def test_javascript_matches_python(case, js_results):
    with create_app().test_request_context("/?lang=en"):
        py = risk.evaluate(case["hours"], open_meteo=case.get("open_meteo", True))
        lines = risk.describe(py, case["hours"])
        recommendation = risk.heat_recommendation(py)
    js = js_results[case["id"]]
    assert js["level"] == py["level"]
    assert js["indicators"] == sorted(py["indicators"])
    assert js["life_hours"] == py["life_hours"]
    assert js["tornado_info"] == py["tornado_info"]
    assert js["tornado_available"] == py["tornado_available"]
    assert js["lines"] == lines
    assert js["recommendation"] == (str(recommendation) if recommendation else None)
    if "IND-CALOR" in py["indicators"]:
        assert js["heat_variant"] == py["indicators"]["IND-CALOR"]["variant"]


def test_javascript_matches_shared_expectations(js_results):
    for case in CASES:
        expected, js = case["expected"], js_results[case["id"]]
        assert js["level"] == expected["level"], case["name"]
        assert js["indicators"] == sorted(expected["indicators"]), case["name"]


def test_tornado_classifier_and_shear():
    script = """
const r = require(process.argv[1]);
const cases = [[50,0,30,15],[500,-2,10,5],[800,-2,18,5],[1500,-3,20,10],[3000,-6,25,15],[null,0,30,15]];
console.log(JSON.stringify({
  levels: cases.map(c => r.tornadoPotential(...c)),
  shear: [r.bulkShear(10,270,30,270), r.bulkShear(10,0,10,180), r.bulkShear(null,0,10,180)],
  tw: r.wetBulb(20, 50),
}));
"""
    proc = subprocess.run([NODE, "-e", script, str(ROOT / "app" / "static" / "risk.js")],
                          capture_output=True, text=True, check=True)
    out = json.loads(proc.stdout)
    assert out["levels"] == ["very_low", "very_low", "low", "moderate", "high", "very_low"]
    assert out["shear"][0] == pytest.approx(20) and out["shear"][1] == pytest.approx(20) and out["shear"][2] is None
    assert out["tw"] == pytest.approx(13.7, abs=0.1)
