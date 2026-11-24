"""Gera os ícones do app instalável (PWA) em app/static/pwa/.

Nuvem com raio (SPEC.md REQ-APP-60) nas cores do design system: fundo #100C08, nuvem em
tinta #F3F4F5 e raio em acento-jeronimo #FB5133. Uso: python3 scripts/build_pwa_icons.py (requer Pillow).
"""
from pathlib import Path

from PIL import Image, ImageDraw

FUNDO, TINTA, ACENTO = "#100C08", "#F3F4F5", "#FB5133"
OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "pwa"
BASE = 2000  # desenha grande e reduz, para bordas suaves


def draw(scale):
    """Desenho numa grade de 1000 unidades, reduzido por `scale` em torno do centro."""
    img = Image.new("RGB", (BASE, BASE), FUNDO)
    d = ImageDraw.Draw(img)
    k = BASE / 1000

    def p(x, y):
        return ((500 + (x - 500) * scale) * k, (500 + (y - 500) * scale) * k)

    def circle(cx, cy, r, fill):
        (x0, y0), (x1, y1) = p(cx - r, cy - r), p(cx + r, cy + r)
        d.ellipse([x0, y0, x1, y1], fill=fill)

    # Nuvem: três círculos sobre uma base de cantos arredondados (todos terminam em y = 665)
    circle(345, 530, 135, TINTA)
    circle(520, 430, 185, TINTA)
    circle(680, 545, 120, TINTA)
    (x0, y0), (x1, y1) = p(345, 520), p(680, 665)
    d.rectangle([x0, y0, x1, y1], fill=TINTA)

    # Raio com respiro na cor do fundo (o mesmo desenho ampliado em volta do centro), para separar da nuvem
    bolt = [(560, 470), (430, 690), (520, 690), (470, 880), (650, 640), (560, 640), (620, 470)]
    cx = sum(x for x, _ in bolt) / len(bolt)
    cy = sum(y for _, y in bolt) / len(bolt)
    gap = [(cx + (x - cx) * 1.22, cy + (y - cy) * 1.12) for x, y in bolt]
    d.polygon([p(*pt) for pt in gap], fill=FUNDO)
    d.polygon([p(*pt) for pt in bolt], fill=ACENTO)
    return img


def save(img, name, size):
    img.resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    full = draw(1.0)
    save(full, "icon-512.png", 512)
    save(full, "icon-192.png", 192)
    save(full, "apple-touch-icon.png", 180)
    save(full, "favicon-32.png", 32)
    # Maskable: o desenho cabe na área segura (círculo de 80% do lado)
    save(draw(0.72), "icon-maskable-512.png", 512)
