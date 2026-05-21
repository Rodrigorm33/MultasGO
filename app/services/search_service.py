"""
Thin wrapper para compatibilidade. Delega tudo para app.search.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.search.engine import (
    pesquisar,
    listar_infracoes,
    listar_com_filtros,
    limpar_cache_palavras_banco,
)
from app.core.cache_manager import cache_manager


def pesquisar_infracoes(query: str, limit: int = 10, skip: int = 0,
                        db: Session = None) -> Dict[str, Any]:
    return pesquisar(query, limit=limit, skip=skip, db=db)


def listar_infracoes_paginado(limit: int = 10, skip: int = 0,
                               db: Session = None) -> Dict[str, Any]:
    return listar_infracoes(limit=limit, skip=skip, db=db)


def listar_infracoes_com_filtros(limit: int = 10, skip: int = 0,
                                  filtros: Dict[str, Any] = None,
                                  db: Session = None) -> Dict[str, Any]:
    return listar_com_filtros(limit=limit, skip=skip, filtros=filtros, db=db)


def limpar_cache_palavras():
    # Limpa cache interno do motor (vocabulário/fuzzy) e caches globais.
    try:
        limpar_cache_palavras_banco()
    except Exception:
        pass
    search_cache = cache_manager.get_cache("search")
    if search_cache:
        search_cache.clear()
