"""
Motor de busca principal do MultasGO.
Extraído e refatorado de search_service.py (1495 linhas → modular).
"""
import re
import time
import html
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.logger import logger
from app.search.in_memory import get_index, invalidate_index
from app.search.normalizer import normalizar, normalizar_para_busca
from app.search.validators import validar_query
from app.search.spell import corretor
from app.search.dictionaries.terms import SINONIMOS, BUSCAS_ESPECIAIS
from app.search import analytics

# Imports opcionais (fallback)
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

try:
    from symspellpy import SymSpell, Verbosity
    SYMSPELL_AVAILABLE = True
except ImportError:
    SYMSPELL_AVAILABLE = False


# === FUNÇÕES AUXILIARES ===

def _expandir_sinonimos(termo_original: str) -> List[str]:
    """Expande termo com sinônimos do dicionário."""
    termo_norm = normalizar(termo_original)
    termos = [termo_original]
    encontrou = False

    for chave, sins in SINONIMOS.items():
        if termo_norm == normalizar(chave):
            termos.extend(sins)
            encontrou = True
            break

    if not encontrou:
        palavras = termo_norm.split()
        for palavra in palavras:
            if len(palavra) >= 3:
                for chave, sins in SINONIMOS.items():
                    if palavra in normalizar(chave):
                        termos.extend(sins)

    if "alcool" in termo_norm:
        termos.extend(["alcool", "influencia", "teste", "recusar", "submetido", "substancia"])

    # Deduplicar preservando ordem
    vistos = set()
    unicos = []
    for t in termos:
        if t not in vistos:
            vistos.add(t)
            unicos.append(t)
    return unicos


def _executar_consulta(
    db: Session, where_clause: str, params: dict,
    limit: int = 10, skip: int = 0,
    order_by_priority: bool = False, search_term: str = None
) -> Any:
    """Executa consulta SQL parametrizada (segura contra SQL injection)."""
    params = dict(params or {})  # evitar mutação do dict recebido
    if order_by_priority and search_term:
        search_term_clean = search_term.lower().strip()
        params["_order_term_space"] = f"% {search_term_clean} %"
        params["_order_term_start"] = f"{search_term_clean} %"
        params["_order_term_end"] = f"% {search_term_clean}"
        params["_order_term_exact"] = search_term_clean
        params["_order_term_prefix"] = f"{search_term_clean}%"
        params["_order_term_contains"] = f"%{search_term_clean}%"

        order_by = """
        ORDER BY
            CASE
                WHEN UPPER("Infração") LIKE UPPER(:_order_term_space)
                  OR UPPER("Infração") LIKE UPPER(:_order_term_start)
                  OR UPPER("Infração") LIKE UPPER(:_order_term_end)
                  OR UPPER("Infração") = UPPER(:_order_term_exact) THEN 1
                WHEN UPPER("Infração") LIKE UPPER(:_order_term_prefix) THEN 2
                WHEN UPPER("Infração") LIKE UPPER(:_order_term_contains) THEN 3
                ELSE 4
            END,
            CASE
                WHEN "Gravidade" LIKE '%Gravissima%' THEN 1
                WHEN "Gravidade" LIKE '%Grave%' THEN 2
                WHEN "Gravidade" LIKE '%Media%' THEN 3
                WHEN "Gravidade" LIKE '%Leve%' THEN 4
                ELSE 5
            END,
            "Pontos" DESC, "Código de Infração"
        """
    else:
        order_by = """
        ORDER BY
            CASE
                WHEN "Gravidade" LIKE '%Gravissima%' THEN 1
                WHEN "Gravidade" LIKE '%Grave%' THEN 2
                WHEN "Gravidade" LIKE '%Media%' THEN 3
                WHEN "Gravidade" LIKE '%Leve%' THEN 4
                ELSE 5
            END,
            "Pontos" DESC, "Código de Infração"
        """

    params["_limit"] = limit
    params["_skip"] = skip
    sql = f"""
    SELECT
        "Código de Infração" as codigo,
        "Infração" as descricao,
        "Responsável" as responsavel,
        "Valor da multa" as valor_multa,
        "Órgão Autuador" as orgao_autuador,
        "Artigos do CTB" as artigos_ctb,
        "Pontos" as pontos,
        "Gravidade" as gravidade
    FROM bdbautos
    WHERE {where_clause}
    {order_by}
    LIMIT :_limit OFFSET :_skip
    """
    return db.execute(text(sql), params)


def _executar_count(db: Session, where_clause: str, params: dict) -> int:
    """Executa COUNT(*) correspondente ao mesmo WHERE da busca (para paginação correta)."""
    params = dict(params or {})
    sql = f"SELECT COUNT(*) as total FROM bdbautos WHERE {where_clause}"
    try:
        return int(db.execute(text(sql), params).scalar() or 0)
    except Exception:
        return 0


def _processar_resultados(result: Any) -> Tuple[List[Dict[str, Any]], int]:
    """Processa rows SQL em lista de dicts formatados."""
    # Defensivo: resultados vão para UI que usa innerHTML em vários pontos.
    # Escapar aqui evita XSS armazenado caso o banco tenha strings maliciosas.
    def _esc(v: Any) -> str:
        s = str(v) if v is not None else ""
        return html.escape(s, quote=True).replace("'", "&#x27;")

    resultados = []
    for row in result:
        try:
            valor_multa = float(row.valor_multa) if row.valor_multa else 0.0
        except (ValueError, TypeError):
            valor_multa = 0.0
        try:
            pontos = int(float(row.pontos)) if row.pontos else 0
        except (ValueError, TypeError):
            pontos = 0
        gravidade = str(row.gravidade).strip() if row.gravidade else "Não informada"
        if gravidade.lower() in ("nan", "none", "null", "undefined"):
            gravidade = "Não informada"

        resultados.append({
            "codigo": _esc(row.codigo) if row.codigo else "",
            "descricao": _esc(row.descricao) if row.descricao else "",
            "responsavel": _esc(row.responsavel) if row.responsavel else "",
            "valor_multa": valor_multa,
            "orgao_autuador": _esc(row.orgao_autuador) if row.orgao_autuador else "",
            "artigos_ctb": _esc(row.artigos_ctb) if row.artigos_ctb else "",
            "pontos": pontos,
            "gravidade": _esc(gravidade),
        })
    return resultados, len(resultados)


def _formatar_docs(docs: List[Any]) -> List[Dict[str, Any]]:
    """Formata docs do índice in-memory no mesmo formato do SQL."""
    def _esc(v: Any) -> str:
        s = str(v) if v is not None else ""
        return html.escape(s, quote=True).replace("'", "&#x27;")

    resultados: List[Dict[str, Any]] = []
    for d in docs:
        resultados.append(
            {
                "codigo": _esc(getattr(d, "codigo", "")),
                "descricao": _esc(getattr(d, "descricao", "")),
                "responsavel": _esc(getattr(d, "responsavel", "")),
                "valor_multa": float(getattr(d, "valor_multa", 0.0) or 0.0),
                "orgao_autuador": _esc(getattr(d, "orgao_autuador", "")),
                "artigos_ctb": _esc(getattr(d, "artigos_ctb", "")),
                "pontos": int(getattr(d, "pontos", 0) or 0),
                "gravidade": _esc(getattr(d, "gravidade", "")),
            }
        )
    return resultados


def _buscar_bafometro(db: Session, limit: int, skip: int) -> Any:
    """Busca especial por códigos de bafômetro."""
    codigos = BUSCAS_ESPECIAIS["bafometro_especial"]
    params = {f"c{i}": c for i, c in enumerate(codigos)}
    placeholders = ", ".join(f":c{i}" for i in range(len(codigos)))
    sql = f"""
    SELECT "Código de Infração" as codigo, "Infração" as descricao,
           "Responsável" as responsavel, "Valor da multa" as valor_multa,
           "Órgão Autuador" as orgao_autuador, "Artigos do CTB" as artigos_ctb,
           "Pontos" as pontos, "Gravidade" as gravidade
    FROM bdbautos
    WHERE "Código de Infração" IN ({placeholders})
    ORDER BY CASE "Código de Infração"
        WHEN '51691' THEN 1 WHEN '75790' THEN 2 WHEN '51692' THEN 3 ELSE 4
    END
    LIMIT :limit OFFSET :skip
    """
    params["limit"] = limit
    params["skip"] = skip
    return db.execute(text(sql), params)


def _buscar_furar_sinal(db: Session, limit: int, skip: int) -> Any:
    """Busca especial por códigos de furar sinal."""
    codigos = BUSCAS_ESPECIAIS["furar_sinal_especial"]
    params = {f"c{i}": c for i, c in enumerate(codigos)}
    placeholders = ", ".join(f":c{i}" for i in range(len(codigos)))
    sql = f"""
    SELECT "Código de Infração" as codigo, "Infração" as descricao,
           "Responsável" as responsavel, "Valor da multa" as valor_multa,
           "Órgão Autuador" as orgao_autuador, "Artigos do CTB" as artigos_ctb,
           "Pontos" as pontos, "Gravidade" as gravidade
    FROM bdbautos
    WHERE "Código de Infração" IN ({placeholders})
    ORDER BY CASE "Código de Infração"
        WHEN '60501' THEN 1 WHEN '60502' THEN 2 WHEN '60503' THEN 3
        WHEN '59591' THEN 4 WHEN '60841' THEN 5 WHEN '56731' THEN 6
        WHEN '56732' THEN 7 ELSE 8
    END
    LIMIT :limit OFFSET :skip
    """
    params["limit"] = limit
    params["skip"] = skip
    return db.execute(text(sql), params)


def _count_codigos_infracao(db: Session, codigos: List[str]) -> int:
    """Conta infrações correspondentes a uma lista de códigos (buscas especiais)."""
    if not codigos:
        return 0
    params = {f"c{i}": c for i, c in enumerate(codigos)}
    placeholders = ", ".join(f":c{i}" for i in range(len(codigos)))
    sql = f'SELECT COUNT(*) as total FROM bdbautos WHERE "Código de Infração" IN ({placeholders})'
    try:
        return int(db.execute(text(sql), params).scalar() or 0)
    except Exception:
        return 0


def _extrair_palavras_banco(db: Session) -> List[str]:
    """Extrai palavras únicas do banco para fuzzy search."""
    if not hasattr(_extrair_palavras_banco, "_cache"):
        result = db.execute(text('SELECT "Infração" as descricao FROM bdbautos'))
        palavras = set()
        for row in result:
            if row.descricao:
                words = re.findall(r'\b\w{3,}\b', normalizar(row.descricao))
                palavras.update(words)
        _extrair_palavras_banco._cache = list(palavras)
        logger.info(f"Cache de palavras: {len(_extrair_palavras_banco._cache)} termos")
    return _extrair_palavras_banco._cache


def _busca_fuzzy(termo: str, db: Session, score_minimo: int = 75) -> List[str]:
    """Busca fuzzy com corretor nativo + prefixos."""
    if not termo or len(termo) < 3:
        return []

    termo_norm = normalizar(termo)
    palavras = _extrair_palavras_banco(db)

    # 1. Prefixo
    prefixos = [p for p in palavras if p.startswith(termo_norm)]
    if prefixos:
        return prefixos[:10]

    # 2. Corretor
    corrigido, conf, _ = corretor.corrigir(termo_norm, palavras, score_minimo / 100.0)
    if conf > 0.5:
        sugestoes = corretor.buscar_sugestoes(termo_norm, palavras, 10)
        encontrados = [s[0] for s in sugestoes if s[1] >= score_minimo / 100.0]
        if encontrados:
            return encontrados

    # 3. RapidFuzz fallback
    if RAPIDFUZZ_AVAILABLE:
        candidatos = [p for p in palavras if abs(len(p) - len(termo_norm)) <= 3]
        if candidatos:
            matches = process.extract(termo_norm, candidatos, scorer=fuzz.WRatio,
                                      limit=10, score_cutoff=score_minimo)
            return [m[0] for m in matches]

    return []


def destacar_resultados(resultados: List[Dict], termos: List[str]) -> List[Dict]:
    """Adiciona <mark> nos termos encontrados na descrição."""
    for r in resultados:
        desc = r.get("descricao", "")
        desc_mark = desc
        for t in termos:
            if len(t) >= 3:
                pattern = re.compile(re.escape(t), re.IGNORECASE)
                desc_mark = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", desc_mark)
        r["descricao_destacada"] = desc_mark
    return resultados


def limpar_cache_palavras_banco() -> None:
    """Limpa caches internos relacionados ao vocabulário/fuzzy da busca."""
    if hasattr(_extrair_palavras_banco, "_cache"):
        try:
            delattr(_extrair_palavras_banco, "_cache")
        except Exception:
            pass
    try:
        corretor.atualizar_vocabulario(set())
    except Exception:
        pass
    try:
        invalidate_index()
    except Exception:
        pass


# === FUNÇÃO PRINCIPAL ===

def pesquisar(query: str, limit: int = 10, skip: int = 0, db: Session = None) -> Dict[str, Any]:
    """
    Função principal de busca. Substitui pesquisar_infracoes().
    """
    start_time = time.time()

    try:
        query_original = query
        logger.info(f"[BUSCA] Busca por: '{query_original}'")

        # Validar query
        erro = validar_query(query_original)
        if erro:
            return erro

        idx = get_index(db)
        docs_page, total, sugestao = idx.search(query_original, limit=limit, skip=skip)
        resultados = _formatar_docs(docs_page)
        tempo_ms = (time.time() - start_time) * 1000
        analytics.registrar_query(query_original, total, tempo_ms)

        if total > 0:
            return {
                "resultados": resultados,
                "total": total,
                "mensagem": f"Encontrados {total} resultados para '{query_original}'.",
                "sugestao": sugestao,
            }

        return {
            "resultados": [],
            "total": 0,
            "mensagem": f"Nenhuma infração encontrada para '{query_original}'.",
            "sugestao": sugestao,
        }

    except Exception as e:
        logger.error(f"[ERRO] Erro na pesquisa: {str(e)}")
        return {"resultados": [], "total": 0,
                "mensagem": "Erro interno. Tente novamente em alguns instantes.",
                "sugestao": None}


# === FUNÇÕES DE LISTAGEM ===

def listar_infracoes(limit: int = 10, skip: int = 0, db: Session = None) -> Dict[str, Any]:
    """Lista infrações com paginação."""
    try:
        sql = """
        SELECT "Código de Infração" as codigo, "Infração" as descricao,
               "Responsável" as responsavel, "Valor da multa" as valor_multa,
               "Órgão Autuador" as orgao_autuador, "Artigos do CTB" as artigos_ctb,
               "Pontos" as pontos, "Gravidade" as gravidade
        FROM bdbautos ORDER BY "Código de Infração" ASC
        LIMIT :limit OFFSET :skip
        """
        result = db.execute(text(sql), {"limit": limit, "skip": skip})
        resultados, _ = _processar_resultados(result)

        count = db.execute(text("SELECT COUNT(*) as total FROM bdbautos")).scalar() or 0
        return {"resultados": resultados, "total": count,
                "mensagem": None if resultados else "Nenhuma infração encontrada"}
    except Exception as e:
        logger.error(f"Erro ao listar: {e}")
        return {"resultados": [], "total": 0, "mensagem": "Erro ao carregar infrações"}


def listar_com_filtros(limit: int = 10, skip: int = 0,
                       filtros: Dict[str, Any] = None, db: Session = None) -> Dict[str, Any]:
    """Lista infrações com filtros."""
    try:
        if filtros is None:
            filtros = {}

        conditions = []
        params = {}

        if filtros.get("gravidade"):
            conditions.append('"Gravidade" LIKE :gravidade')
            params["gravidade"] = f"%{filtros['gravidade']}%"
        if filtros.get("responsavel"):
            conditions.append('"Responsável" LIKE :responsavel')
            params["responsavel"] = f"%{filtros['responsavel']}%"
        if filtros.get("orgao"):
            conditions.append('"Órgão Autuador" LIKE :orgao')
            params["orgao"] = f"%{filtros['orgao']}%"
        if filtros.get("busca"):
            conditions.append('"Infração" LIKE :busca')
            params["busca"] = f"%{filtros['busca']}%"
        if filtros.get("pontos_min") is not None:
            conditions.append('CAST("Pontos" AS INTEGER) >= :pontos_min')
            params["pontos_min"] = filtros["pontos_min"]
        if filtros.get("pontos_max") is not None:
            conditions.append('CAST("Pontos" AS INTEGER) <= :pontos_max')
            params["pontos_max"] = filtros["pontos_max"]

        where = " AND ".join(conditions) if conditions else "1=1"

        if conditions:
            order = 'ORDER BY "Código de Infração" ASC'
        else:
            order = """ORDER BY
                CASE "Gravidade"
                    WHEN 'Gravissima3X' THEN 1 WHEN 'Gravissima2X' THEN 2
                    WHEN 'Gravissima' THEN 3 WHEN 'Grave' THEN 4
                    WHEN 'Media' THEN 5 WHEN 'Leve' THEN 6
                    WHEN 'Nao ha' THEN 6 ELSE 7
                END ASC, "Código de Infração" ASC"""

        sql = f"""
        SELECT "Código de Infração" as codigo, "Infração" as descricao,
               "Responsável" as responsavel, "Valor da multa" as valor_multa,
               "Órgão Autuador" as orgao_autuador, "Artigos do CTB" as artigos_ctb,
               "Pontos" as pontos, "Gravidade" as gravidade
        FROM bdbautos WHERE {where} {order}
        LIMIT :limit OFFSET :skip
        """
        params["limit"] = limit
        params["skip"] = skip

        result = db.execute(text(sql), params)
        resultados, _ = _processar_resultados(result)

        count_params = {k: v for k, v in params.items() if k not in ("limit", "skip")}
        count = db.execute(text(f"SELECT COUNT(*) FROM bdbautos WHERE {where}"), count_params).scalar() or 0

        msg = None
        if not resultados and conditions:
            msg = "Nenhuma infração encontrada com os filtros aplicados"
        elif not resultados:
            msg = "Nenhuma infração encontrada"

        return {
            "resultados": resultados, "total": count, "mensagem": msg,
            "filtros_aplicados": [k for k, v in filtros.items() if v is not None]
        }
    except Exception as e:
        logger.error(f"Erro ao listar com filtros: {e}")
        return {"resultados": [], "total": 0, "mensagem": "Erro ao carregar infrações com filtros"}
