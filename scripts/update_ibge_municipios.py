"""
Atualiza app/data/municipios_ibge.json a partir da API de localidades do IBGE.

Uso: python scripts/update_ibge_municipios.py [arquivo_json_baixado]

O servidor do IBGE costuma servir uma cadeia de certificados incompleta, o que faz
o `requests` falhar. Nesse caso, baixe o JSON manualmente (navegador ou curl):
  curl -o municipios.json "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
e passe o caminho do arquivo como argumento.
"""
import json
import sys
from pathlib import Path

import requests

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
OUTPUT = Path(__file__).resolve().parent.parent / "app" / "data" / "municipios_ibge.json"


def main():
    if len(sys.argv) > 1:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        data = requests.get(URL, timeout=60).json()

    states, municipalities = {}, {}
    for m in data:
        uf = m["UF-sigla"]
        states[uf] = m["UF-nome"]
        municipalities.setdefault(uf, {})[m["municipio-nome"]] = m["municipio-id"]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": URL, "states": dict(sorted(states.items())),
               "municipalities": {uf: dict(sorted(v.items())) for uf, v in sorted(municipalities.items())}}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{sum(len(v) for v in municipalities.values())} municípios salvos em {OUTPUT}")


if __name__ == "__main__":
    main()
