"""Ponto de entrada: `python wsgi.py` (desenvolvimento) ou `gunicorn wsgi:app` (produção)."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
