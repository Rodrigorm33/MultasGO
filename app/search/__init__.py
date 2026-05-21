"""
Módulo de busca consolidado do MultasGO.
API pública para busca, autocomplete e analytics.
"""
from app.search.engine import (
    pesquisar,
    listar_infracoes,
    listar_com_filtros,
    destacar_resultados,
    limpar_cache_palavras_banco,
)
from app.search.autocomplete import autocomplete, obter_termos_populares
from app.search.analytics import (
    registrar_query, obter_estatisticas,
    obter_queries_populares, obter_queries_sem_resultado,
)
from app.search.spell import corretor

__all__ = [
    'pesquisar',
    'listar_infracoes',
    'listar_com_filtros',
    'destacar_resultados',
    'limpar_cache_palavras_banco',
    'autocomplete',
    'obter_termos_populares',
    'registrar_query',
    'obter_estatisticas',
    'obter_queries_populares',
    'obter_queries_sem_resultado',
    'corretor',
]
