"""Validação de queries de busca (estilo Google: texto livre com limites seguros)."""

import re
from typing import Any, Dict, Optional


MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 200


def validar_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Valida query de busca.

    Regras:
    - Aceita múltiplas palavras (sem limite de palavras), como um motor de busca.
    - Limita tamanho total para evitar abuso.
    - Bloqueia apenas caracteres de controle.
    """
    if not query or len(query.strip()) < MIN_QUERY_LENGTH:
        return {
            "resultados": [],
            "total": 0,
            "mensagem": f"Digite pelo menos {MIN_QUERY_LENGTH} caracteres para pesquisar.",
        }

    if len(query.strip()) > MAX_QUERY_LENGTH:
        return {
            "resultados": [],
            "total": 0,
            "mensagem": f"Sua busca é muito longa. Use até {MAX_QUERY_LENGTH} caracteres.",
        }

    # Control chars (inclui CR/LF). Evita payloads estranhos e log injection.
    if re.search(r"[\x00-\x1F\x7F]", query):
        return {"resultados": [], "total": 0, "mensagem": "A busca contém caracteres inválidos."}

    return None
