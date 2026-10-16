"""Teste manual contra as APIs reais: python scripts/test_api.py "Porto Alegre" """
import pprint
import sys
from pathlib import Path

# garantir que a raiz do projeto esteja no sys.path para importar o pacote app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.services import forecast, geocoding, inmet

city_query = sys.argv[1] if len(sys.argv) > 1 else "Sao Paulo"
pp = pprint.PrettyPrinter(indent=2, width=120)

with create_app().test_request_context():
    city = geocoding.find_city(city_query, "pt")
    print("\nCidade:")
    pp.pprint(city)

    weather = forecast.get_weather(city["latitude"], city["longitude"])
    print("\nCondições atuais:")
    pp.pprint({k: str(v) for k, v in weather["current"].items()})

    print("\nPrevisão 7 dias:")
    for day in weather["daily"]:
        print(f"  {day['date']}  {day['temp_min']}–{day['temp_max']}°C  UR {day['humidity_mean']}%  "
              f"{day['pressure']['value']} hPa ({day['pressure']['key']})  tornado: {day['tornado']['key']}  "
              f"bulbo úmido máx: {day['wet_bulb_max']}°C")

    if city["country_code"] == "BR":
        alerts = inmet.get_alerts_for_city(city["name"], city["state"], city["latitude"], city["longitude"])
        print(f"\nAvisos INMET (IBGE {alerts['ibge_code']}):")
        for a in alerts["alerts"]:
            print(f"  [{a['severity']}] {a['event']}  {a['start']} → {a['end']}")
        if not alerts["alerts"]:
            print("  nenhum aviso ativo")
