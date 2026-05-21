"""Normalização de texto para busca."""
import re
from unidecode import unidecode


def normalizar(texto: str) -> str:
    """Normalização completa: remove acentos, especiais, colapsa espaços."""
    if not texto:
        return ""
    texto = unidecode(texto.strip().lower())
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


def normalizar_para_busca(texto: str) -> str:
    """Normalização leve: remove acentos e lowercase."""
    if not texto:
        return ""
    return unidecode(texto.strip().lower())
