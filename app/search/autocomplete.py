"""Sistema de autocomplete para busca de infrações."""
from typing import List, Dict, Tuple
from app.search.dictionaries.terms import SINONIMOS, TERMOS_PRIORITARIOS
from app.search.normalizer import normalizar

_termos_index: List[Tuple[str, str]] = []  # (termo_original, termo_normalizado)
_initialized: bool = False


def _inicializar():
    """Constrói índice de autocomplete a partir do dicionário."""
    global _termos_index, _initialized
    termos = set(SINONIMOS.keys()) | TERMOS_PRIORITARIOS
    # Filtrar compostos com espaço e manter apenas termos simples
    simples = [t for t in termos if ' ' not in t]
    _termos_index = sorted([(t, normalizar(t)) for t in simples], key=lambda x: x[1])
    _initialized = True


def autocomplete(prefixo: str, limite: int = 10) -> List[Dict[str, str]]:
    """
    Retorna sugestões de autocomplete para um prefixo.
    Target: <10ms de latência.
    """
    if not _initialized:
        _inicializar()

    if not prefixo or len(prefixo) < 2:
        return []

    prefixo_norm = normalizar(prefixo)
    resultados = []

    # Primeiro: matches por prefixo
    for termo, termo_norm in _termos_index:
        if termo_norm.startswith(prefixo_norm):
            resultados.append({"termo": termo, "tipo": "prefixo"})

    # Depois: matches por conteúdo (se ainda tem espaço)
    if len(resultados) < limite:
        for termo, termo_norm in _termos_index:
            if not termo_norm.startswith(prefixo_norm) and prefixo_norm in termo_norm:
                resultados.append({"termo": termo, "tipo": "contem"})
                if len(resultados) >= limite:
                    break

    # Ordenar: prefixo primeiro, depois por tamanho
    resultados.sort(key=lambda x: (0 if x["tipo"] == "prefixo" else 1, len(x["termo"])))
    return resultados[:limite]


def obter_termos_populares(limite: int = 20) -> List[str]:
    """Retorna termos populares/sugeridos para busca."""
    if not _initialized:
        _inicializar()
    return sorted(list(TERMOS_PRIORITARIOS))[:limite]
