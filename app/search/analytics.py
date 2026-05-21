"""Analytics de queries de busca - thread-safe."""
import threading
from typing import Dict, List
from dataclasses import dataclass, field
from collections import Counter, deque


@dataclass
class QueryStats:
    total_searches: int = 0
    queries_com_resultado: int = 0
    queries_sem_resultado: int = 0
    tempo_medio_ms: float = 0.0


# NOTE: Este módulo é chamado em toda busca. Sem limites, ele cresce indefinidamente
# (Counter com chaves únicas + lista de tempos), o que pode virar DoS por memória.
# Mantemos amostras e cardinalidade sob controle, preservando utilidade (top queries).
MAX_UNIQUE_QUERIES: int = 5000
MAX_TIME_SAMPLES: int = 5000

_lock = threading.Lock()
_queries: Counter = Counter()
_queries_sem_resultado: Counter = Counter()
_tempos = deque(maxlen=MAX_TIME_SAMPLES)
_total: int = 0
_com_resultado: int = 0


def _compactar_counters_se_necessario() -> None:
    """Limita cardinalidade dos counters para evitar crescimento ilimitado."""
    global _queries, _queries_sem_resultado

    # Evitar compactação constante: quando estoura, reduz para 90% do limite.
    target = int(MAX_UNIQUE_QUERIES * 0.9)
    if target < 1:
        target = 1

    if len(_queries) > MAX_UNIQUE_QUERIES:
        _queries = Counter(dict(_queries.most_common(target)))
    if len(_queries_sem_resultado) > MAX_UNIQUE_QUERIES:
        _queries_sem_resultado = Counter(dict(_queries_sem_resultado.most_common(target)))


def registrar_query(query: str, total_resultados: int, tempo_ms: float):
    """Registra execução de query para analytics."""
    global _total, _com_resultado
    with _lock:
        # Normalizar chave (defensivo: evita None e strings enormes vindas de outros chamadores)
        query_key = (query or "").lower().strip()[:200]

        # Tempo defensivo (evita valores quebrados contaminarem média)
        try:
            tempo_ms_val = float(tempo_ms)
            if tempo_ms_val < 0:
                tempo_ms_val = 0.0
        except (TypeError, ValueError):
            tempo_ms_val = 0.0

        _total += 1
        _queries[query_key] += 1
        _tempos.append(tempo_ms_val)
        if total_resultados > 0:
            _com_resultado += 1
        else:
            _queries_sem_resultado[query_key] += 1

        _compactar_counters_se_necessario()


def obter_estatisticas() -> QueryStats:
    """Retorna estatísticas gerais."""
    with _lock:
        tempo_medio = (sum(_tempos) / len(_tempos)) if _tempos else 0.0
        return QueryStats(
            total_searches=_total,
            queries_com_resultado=_com_resultado,
            queries_sem_resultado=_total - _com_resultado,
            tempo_medio_ms=round(tempo_medio, 2),
        )


def obter_queries_populares(limite: int = 20) -> List[Dict]:
    """Retorna queries mais populares."""
    with _lock:
        return [
            {"query": q, "count": c}
            for q, c in _queries.most_common(limite)
        ]


def obter_queries_sem_resultado(limite: int = 20) -> List[Dict]:
    """Retorna queries que não retornaram resultados."""
    with _lock:
        return [
            {"query": q, "count": c}
            for q, c in _queries_sem_resultado.most_common(limite)
        ]
