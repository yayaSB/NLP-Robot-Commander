import re
import unicodedata


def normalize_text(text: str) -> str:
    """Normalise la casse, les accents et les espaces pour les règles lexicales."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    without_punctuation = re.sub(r"[^a-z0-9'\s-]", " ", without_accents)
    return re.sub(r"\s+", " ", without_punctuation).strip()

