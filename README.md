# Wet Bulb Temperature Calculator

## Purpose
A web tool that calculates the **wet bulb temperature** for any city from real-time weather data, and shows a
**7-day forecast** with relative humidity, high/low pressure systems and an experimental **tornado potential**
indicator. For Brazilian cities it also shows the **official INMET weather alerts**.

The wet bulb temperature is an important measure for assessing thermal comfort and heat stress — above ~35 °C
the human body can no longer cool itself (Sherwood & Huber, 2010).

## Features
- **Current conditions**: temperature, feels-like, relative humidity, dew point, sea-level pressure, wind and gusts.
- **Wet bulb temperature** (Stull, 2011) with heat-stress risk levels, now and as a daily maximum in the forecast.
- **7-day forecast**: min/max temperature, mean/min/max relative humidity, rain probability and amount, gusts.
- **Pressure index**: **A** high pressure (≥ 1020 hPa), **B** low pressure (≤ 1008 hPa), and trend vs. the previous day.
- **Tornado potential** (very low / low / moderate / high): derived hourly from CAPE, lifted index, deep-layer
  (surface–500 hPa) and low-level (surface–850 hPa) wind shear using the WMAXSHEAR parameter
  (Taszarek et al., 2020). *Experimental — not an official forecast.*
- **INMET alerts** (Brazil only): active and upcoming alerts with severity, risks and instructions, matched to the
  city by IBGE code (with a fallback to the alert polygon).
- Interface in English, Portuguese and Spanish.

## Data sources
| Data | Source | Key required |
|------|--------|--------------|
| Forecast and current weather | [Open-Meteo](https://open-meteo.com/) — best-match blend of ECMWF, DWD ICON, NOAA GFS and other models | No |
| City search | [Open-Meteo Geocoding](https://open-meteo.com/en/docs/geocoding-api) (GeoNames) | No |
| Official alerts | [INMET](https://avisos.inmet.gov.br) — `apiprevmet3.inmet.gov.br/avisos/ativos` | No |
| Municipality codes | [IBGE](https://servicodados.ibge.gov.br/api/docs/localidades) (bundled in `app/data/`) | No |

## Project structure
```
app/
  __init__.py          # create_app() factory, Babel setup
  config.py            # settings (SECRET_KEY from environment)
  routes.py            # web routes
  meteo/               # pure calculations: wet bulb, pressure & tornado indices, WMO weather codes
  services/            # external APIs: geocoding, forecast (Open-Meteo), INMET alerts, HTTP/cache helpers
  data/                # bundled IBGE municipality table
  templates/           # base.html, index.html and partials/
  static/              # CSS
  translations/        # pt and es catalogs
scripts/               # manual API check, IBGE table updater, translation helper
tests/                 # pytest suite (no network access needed)
wsgi.py                # entry point
```

## How to use
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
python wsgi.py                # http://localhost:5000
```
Search for a city by name; add a country, state or Brazilian UF to disambiguate:
`Paris, FR`, `Moore, Oklahoma`, `Santa Maria, RS`.

In production set a `SECRET_KEY` environment variable and run `gunicorn wsgi:app` (see `Dockerfile`).

### Tests and maintenance
```bash
pytest                                        # unit tests
python scripts/test_api.py "Porto Alegre"     # manual check against the real APIs
pybabel extract -F babel.cfg -k _l -o messages.pot .
pybabel update -i messages.pot -d app/translations
pybabel compile -d app/translations
python scripts/update_ibge_municipios.py      # refresh the IBGE municipality table
```

## Contributing
If you would like to contribute to this project, feel free to open an issue or submit a pull request.
Your feedback and suggestions are always welcome!
