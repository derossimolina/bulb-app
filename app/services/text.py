import unicodedata


def normalize(text):
    """Minúsculas, sem acentos, apóstrofos ou hífens e com espaços colapsados."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.replace("'", "").replace("-", " ").lower().split())
