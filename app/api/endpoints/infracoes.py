from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import re
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Path, HTTPException, status, Response, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import get_db
from app.models.infracao_model import InfracaoModel
from app.schemas.infracao_schema import InfracaoPesquisaResponse, InfracaoSchema
from app.services import search_service
from app.core.logger import logger

# Constantes
MAX_CACHE_SIZE = 1000
CACHE_TTL_LISTA = 300  # 5 minutos
CACHE_TTL_DETALHE = 3600  # 1 hora
MAX_QUERY_LENGTH = 100
MIN_QUERY_LENGTH = 2

router = APIRouter(
    tags=["infrações"],
    responses={
        400: {
            "description": "Requisição inválida",
            "content": {
                "application/json": {
                    "example": {"detail": "Parâmetros inválidos"}
                }
            }
        },
        500: {
            "description": "Erro interno do servidor",
            "content": {
                "application/json": {
                    "example": {"detail": "Erro interno do servidor. Por favor, tente novamente mais tarde."}
                }
            }
        },
        503: {
            "description": "Serviço indisponível - Banco de dados não acessível",
            "content": {
                "application/json": {
                    "example": {"detail": "Erro ao acessar o banco de dados. Por favor, tente novamente mais tarde."}
                }
            }
        }
    }
)

# Queries SQL otimizadas com hints de índice
SQL_SELECT_INFRACOES = """
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
"""

def validar_codigo_infracao(codigo: str) -> bool:
    """Valida o formato do código de infração (sem hífens)."""
    # Formato esperado: XXXXX (4 ou 5 dígitos)
    # Esta função deve receber o código já sem hífens
    padrao = r'^\d{4,5}$'
    return bool(re.match(padrao, codigo))

def validar_query_pesquisa(query: str) -> None:
    """Valida o termo de pesquisa."""
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O termo de pesquisa não pode estar vazio"
        )
    
    if len(query) < MIN_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O termo de pesquisa deve ter pelo menos {MIN_QUERY_LENGTH} caracteres"
        )
    
    if len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O termo de pesquisa não pode ter mais que {MAX_QUERY_LENGTH} caracteres"
        )
    
    # Verificar caracteres especiais ou potencialmente maliciosos
    caracteres_invalidos = re.compile(r'[<>{}[\]"\'`;()]')
    if caracteres_invalidos.search(query):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O termo de pesquisa contém caracteres inválidos"
        )

def validar_parametros_paginacao(skip: int, limit: int) -> None:
    """Valida os parâmetros de paginação."""
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O parâmetro 'skip' não pode ser negativo"
        )
    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O parâmetro 'limit' deve ser maior que zero"
        )
    if limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O parâmetro 'limit' não pode ser maior que 100"
        )

def validar_dados_infracao(infracao: InfracaoSchema) -> None:
    """Valida os dados de uma infração."""
    if not infracao.codigo or len(infracao.codigo) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código da infração deve ter pelo menos 4 caracteres"
        )
    
    if not infracao.descricao or len(infracao.descricao.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Descrição da infração deve ter pelo menos 10 caracteres"
        )
    
    if not infracao.responsavel or len(infracao.responsavel.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Responsável deve ter pelo menos 2 caracteres"
        )
    
    if infracao.valor_multa <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor da multa deve ser maior que zero"
        )
    
    if not infracao.orgao_autuador or len(infracao.orgao_autuador.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Órgão autuador deve ter pelo menos 2 caracteres"
        )
    
    if not infracao.artigos_ctb or len(infracao.artigos_ctb.strip()) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Artigos do CTB são obrigatórios"
        )
    
    if infracao.pontos < 0 or infracao.pontos > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pontos deve estar entre 0 e 20"
        )
    
    if not infracao.gravidade or len(infracao.gravidade.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gravidade deve ter pelo menos 3 caracteres"
        )

def registrar_metrica(request: Request, inicio: float, endpoint: str) -> None:
    """Registra métricas de tempo de resposta e uso."""
    tempo_resposta = time.time() - inicio
    logger.info(
        f"Métrica - Endpoint: {endpoint}, "
        f"IP: {request.client.host}, "
        f"Tempo: {tempo_resposta:.3f}s, "
        f"Data: {datetime.now().isoformat()}"
    )

def processar_resultados(result: Any) -> Tuple[List[Dict[str, Any]], int]:
    """
    Processa os resultados da consulta SQL, formatando e validando os valores.
    
    Args:
        result: Resultado da consulta SQL
        
    Returns:
        Tupla contendo lista de resultados formatados e o total de resultados
    """
    resultados = []
    for row in result:
        # Tratar valor_multa como float
        try:
            valor_multa = float(row.valor_multa) if row.valor_multa else 0.0
        except (ValueError, TypeError):
            valor_multa = 0.0
            
        # Tratar pontos como int
        try:
            pontos = int(float(row.pontos)) if row.pontos else 0
        except (ValueError, TypeError):
            pontos = 0
            
        # Normalizar gravidade
        gravidade = str(row.gravidade).strip() if row.gravidade else "Não informada"
        if gravidade.lower() in ["nan", "none", "null", "undefined"]:
            gravidade = "Não informada"
            
        resultados.append({
            "codigo": str(row.codigo) if row.codigo else "",
            "descricao": str(row.descricao) if row.descricao else "",
            "responsavel": str(row.responsavel) if row.responsavel else "",
            "valor_multa": valor_multa,
            "orgao_autuador": str(row.orgao_autuador) if row.orgao_autuador else "",
            "artigos_ctb": str(row.artigos_ctb) if row.artigos_ctb else "",
            "pontos": pontos,
            "gravidade": gravidade
        })
        
    return resultados, len(resultados)

@lru_cache(maxsize=MAX_CACHE_SIZE)
def converter_row_para_schema(
    codigo: str,
    descricao: str,
    responsavel: str,
    valor_multa: float,
    orgao_autuador: str,
    artigos_ctb: str,
    pontos: int,
    gravidade: str
) -> InfracaoSchema:
    """Converte dados para InfracaoSchema com cache."""
    try:
        valor_multa_float = float(valor_multa) if valor_multa else 0.0
    except (ValueError, TypeError):
        valor_multa_float = 0.0

    try:
        pontos_int = int(float(pontos)) if pontos else 0
    except (ValueError, TypeError):
        pontos_int = 0
    
    # Tratar "Nao ha" como "Leve" para exibição
    gravidade_display = "Leve" if str(gravidade) == "Nao ha" else str(gravidade) if gravidade else ""

    return InfracaoSchema(
        codigo=str(codigo) if codigo else "",
        descricao=str(descricao) if descricao else "",
        responsavel=str(responsavel) if responsavel else "",
        valor_multa=valor_multa_float,
        orgao_autuador=str(orgao_autuador) if orgao_autuador else "",
        artigos_ctb=str(artigos_ctb) if artigos_ctb else "",
        pontos=pontos_int,
        gravidade=gravidade_display
    )

def converter_row_objeto(row: Any) -> InfracaoSchema:
    """Converte um objeto row para InfracaoSchema usando cache."""
    return converter_row_para_schema(
        codigo=row.codigo,
        descricao=row.descricao,
        responsavel=row.responsavel,
        valor_multa=row.valor_multa,
        orgao_autuador=row.orgao_autuador,
        artigos_ctb=row.artigos_ctb,
        pontos=row.pontos,
        gravidade=row.gravidade
    )

def converter_dict_para_schema(item: Dict[str, Any]) -> InfracaoSchema:
    """Converte um dicionário para InfracaoSchema usando cache."""
    # Tratar "Nao ha" como "Leve" para exibição
    gravidade_original = item.get("gravidade", "")
    gravidade_display = "Leve" if gravidade_original == "Nao ha" else gravidade_original

    return converter_row_para_schema(
        codigo=item.get("codigo", ""),
        descricao=item.get("descricao", ""),
        responsavel=item.get("responsavel", ""),
        valor_multa=item.get("valor_multa", 0.0),
        orgao_autuador=item.get("orgao_autuador", ""),
        artigos_ctb=item.get("artigos_ctb", ""),
        pontos=item.get("pontos", 0),
        gravidade=gravidade_display
    )

@router.get(
    "/",
    response_model=List[InfracaoSchema],
    summary="Listar infrações",
    description="Retorna uma lista paginada de todas as infrações disponíveis, ordenadas por código.",
    responses={
        200: {
            "description": "Lista de infrações recuperada com sucesso",
            "content": {
                "application/json": {
                    "example": [{
                        "codigo": "5169-1",
                        "descricao": "Dirigir sob influência de álcool",
                        "responsavel": "Condutor",
                        "valor_multa": 2934.70,
                        "orgao_autuador": "Estadual",
                        "artigos_ctb": "165",
                        "pontos": 7,
                        "gravidade": "Gravíssima"
                    }]
                }
            }
        }
    }
)
def listar_infracoes(
    request: Request,
    response: Response,
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, gt=0, le=100, description="Número máximo de registros para retornar"),
    db: Session = Depends(get_db)
):
    """Lista todas as infrações disponíveis."""
    inicio = time.time()
    try:
        validar_parametros_paginacao(skip, limit)
        
        sql = f"{SQL_SELECT_INFRACOES} ORDER BY \"Código de Infração\" LIMIT :limit OFFSET :skip"
        result = db.execute(text(sql), {"limit": limit, "skip": skip})
        
        # Adiciona cache headers
        response.headers["Cache-Control"] = f"public, max-age={CACHE_TTL_LISTA}"
        response.headers["Vary"] = "Accept-Encoding"
        
        infracoes = [converter_row_objeto(row) for row in result]
        registrar_metrica(request, inicio, "listar_infracoes")
        return infracoes

    except SQLAlchemyError as e:
        logger.error(f"Erro ao listar infrações: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erro ao acessar o banco de dados. Por favor, tente novamente mais tarde."
        )
    except Exception as e:
        logger.error(f"Erro inesperado ao listar infrações: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor. Por favor, tente novamente mais tarde."
        )

@router.get(
    "/pesquisa",
    response_model=InfracaoPesquisaResponse,
    summary="Pesquisar infrações",
    description="Pesquisa infrações por código ou descrição, retornando resultados paginados.",
    responses={
        200: {
            "description": "Pesquisa realizada com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "resultados": [{
                            "codigo": "5169-1",
                            "descricao": "Dirigir sob influência de álcool",
                            "responsavel": "Condutor",
                            "valor_multa": 2934.70,
                            "orgao_autuador": "Estadual",
                            "artigos_ctb": "165",
                            "pontos": 7,
                            "gravidade": "Gravíssima"
                        }],
                        "total": 1,
                        "mensagem": None,
                        "sugestao": None
                    }
                }
            }
        }
    }
)
def pesquisar(
    request: Request,
    q: Optional[str] = Query(None, min_length=MIN_QUERY_LENGTH, max_length=MAX_QUERY_LENGTH, description="Termo de pesquisa (compatibilidade frontend)"),
    query: Optional[str] = Query(None, min_length=MIN_QUERY_LENGTH, max_length=MAX_QUERY_LENGTH, description="Termo de pesquisa"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(10, gt=0, le=100, description="Número máximo de registros para retornar"),
    db: Session = Depends(get_db),
    response: Response = None
):
    """Pesquisa infrações por código ou descrição. Aceita tanto 'q' quanto 'query' como parâmetros de pesquisa."""
    inicio = time.time()
    try:
        # Usar 'q' se fornecido, senão usar 'query'
        search_term = q if q is not None else query
        
        # Verificar se pelo menos um dos parâmetros de pesquisa foi fornecido
        if search_term is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O termo de pesquisa é obrigatório (use 'q' ou 'query')"
            )
        
        validar_parametros_paginacao(skip, limit)
        validar_query_pesquisa(search_term)
        
        resultado = search_service.pesquisar_infracoes(search_term, limit=limit, skip=skip, db=db)
        
        # Adiciona cache headers
        if response:
            response.headers["Cache-Control"] = f"public, max-age={CACHE_TTL_LISTA}"
            response.headers["Vary"] = "Accept-Encoding"
        
        resultado_pesquisa = InfracaoPesquisaResponse(
            resultados=[converter_dict_para_schema(item) for item in resultado.get("resultados", [])],
            total=resultado.get("total", 0),
            mensagem=resultado.get("mensagem"),
            sugestao=resultado.get("sugestao")
        )
        
        registrar_metrica(request, inicio, "pesquisar")
        return resultado_pesquisa

    except SQLAlchemyError as e:
        logger.error(f"Erro ao pesquisar infrações: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erro ao acessar o banco de dados. Por favor, tente novamente mais tarde."
        )
    except HTTPException as e:
        logger.error(f"Erro de validação na pesquisa: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao pesquisar infrações: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor. Por favor, tente novamente mais tarde."
        )

# NOVO EXPLORADOR - SIMPLES E FUNCIONAL
@router.get(
    "/explorador",
    response_model=InfracaoPesquisaResponse,
    summary="Explorador de infrações",
    description="Lista todas as infrações com paginação simples",
    responses={
        200: {"description": "Lista de infrações carregada com sucesso"}
    }
)
def explorador_infracoes(
    request: Request,
    skip: int = Query(0, ge=0, description="Registros para pular"),
    limit: int = Query(10, gt=0, le=100, description="Máximo de registros"),
    gravidade: Optional[str] = Query(None, description="Filtrar por gravidade (Leve, Média, Grave, Gravíssima)"),
    responsavel: Optional[str] = Query(None, description="Filtrar por responsável (Condutor, Proprietário)"),
    orgao: Optional[str] = Query(None, description="Filtrar por órgão autuador"),
    pontos_min: Optional[int] = Query(None, ge=0, le=20, description="Pontos mínimos"),
    pontos_max: Optional[int] = Query(None, ge=0, le=20, description="Pontos máximos"),
    busca: Optional[str] = Query(None, description="Busca textual na descrição"),
    db: Session = Depends(get_db)
):
    """Explorador com filtros e paginação"""
    inicio = time.time()
    try:
        validar_parametros_paginacao(skip, limit)

        # Criar filtros (apenas com valores válidos)
        filtros = {}
        if gravidade:
            filtros["gravidade"] = gravidade
        if responsavel:
            filtros["responsavel"] = responsavel
        if orgao:
            filtros["orgao"] = orgao
        if pontos_min is not None:
            filtros["pontos_min"] = pontos_min
        if pontos_max is not None:
            filtros["pontos_max"] = pontos_max
        if busca:
            filtros["busca"] = busca

        # SEMPRE usar ordenação por gravidade
        from sqlalchemy import text

        # Construir WHERE clause se há filtros
        where_conditions = []
        params = {"limit": limit, "skip": skip}

        if filtros.get("gravidade"):
            where_conditions.append("\"Gravidade\" LIKE :gravidade")
            params["gravidade"] = f"%{filtros['gravidade']}%"

        if filtros.get("responsavel"):
            where_conditions.append("\"Responsável\" LIKE :responsavel")
            params["responsavel"] = f"%{filtros['responsavel']}%"

        if filtros.get("orgao"):
            where_conditions.append("\"Órgão Autuador\" LIKE :orgao")
            params["orgao"] = f"%{filtros['orgao']}%"

        if filtros.get("busca"):
            where_conditions.append("\"Infração\" LIKE :busca")
            params["busca"] = f"%{filtros['busca']}%"

        if filtros.get("pontos_min") is not None:
            where_conditions.append("CAST(\"Pontos\" AS INTEGER) >= :pontos_min")
            params["pontos_min"] = filtros["pontos_min"]

        if filtros.get("pontos_max") is not None:
            where_conditions.append("CAST(\"Pontos\" AS INTEGER) <= :pontos_max")
            params["pontos_max"] = filtros["pontos_max"]

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Query sempre com ordenação por gravidade
        sql_query = f"""
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
        ORDER BY
            CASE "Gravidade"
                WHEN 'Gravissima3X' THEN 1
                WHEN 'Gravissima2X' THEN 2
                WHEN 'Gravissima' THEN 3
                WHEN 'Grave' THEN 4
                WHEN 'Media' THEN 5
                WHEN 'Leve' THEN 6
                WHEN 'Nao ha' THEN 6
                ELSE 7
            END ASC,
            "Código de Infração" ASC
        LIMIT :limit OFFSET :skip
        """

        resultado_db = db.execute(text(sql_query), params)
        rows = resultado_db.fetchall()

        # Converter resultados
        resultados = []
        for row in rows:
            # Tratar "Nao ha" como "Leve" para exibição
            gravidade_display = "Leve" if row.gravidade == "Nao ha" else str(row.gravidade)

            resultados.append({
                "codigo": str(row.codigo),
                "descricao": str(row.descricao),
                "responsavel": str(row.responsavel),
                "valor_multa": float(row.valor_multa) if row.valor_multa not in ['Nao ha', None] else 0.0,
                "orgao_autuador": str(row.orgao_autuador),
                "artigos_ctb": str(row.artigos_ctb),
                "pontos": int(row.pontos) if str(row.pontos).isdigit() else 0,
                "gravidade": gravidade_display
            })

        # Contar total
        count_query = f"SELECT COUNT(*) as total FROM bdbautos WHERE {where_clause}"
        count_params = {k: v for k, v in params.items() if k not in ['limit', 'skip']}
        count_result = db.execute(text(count_query), count_params)
        total = count_result.scalar()

        resultado = {
            "resultados": resultados,
            "total": total,
            "mensagem": None
        }

        resultado_explorador = InfracaoPesquisaResponse(
            resultados=[converter_dict_para_schema(item) for item in resultado.get("resultados", [])],
            total=resultado.get("total", 0),
            mensagem=resultado.get("mensagem"),
            sugestao=None
        )

        registrar_metrica(request, inicio, "explorador")
        return resultado_explorador

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Erro no explorador: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.get(
    "/{codigo}",
    response_model=InfracaoSchema,
    summary="Obter infração por código",
    description="Retorna os detalhes de uma infração específica pelo seu código.",
    responses={
        200: {
            "description": "Infração encontrada com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "codigo": "5169-1",
                        "descricao": "Dirigir sob influência de álcool",
                        "responsavel": "Condutor",
                        "valor_multa": 2934.70,
                        "orgao_autuador": "Estadual",
                        "artigos_ctb": "165",
                        "pontos": 7,
                        "gravidade": "Gravíssima"
                    }
                }
            }
        },
        404: {
            "description": "Infração não encontrada",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Infração com código XXX não encontrada"
                    }
                }
            }
        }
    }
)
def obter_infracao(
    request: Request,
    response: Response,
    codigo: str = Path(..., min_length=1, max_length=50, description="Código da infração"),
    db: Session = Depends(get_db)
):
    inicio = time.time()
    try:
        # Guardar o código original para mensagens
        codigo_original = codigo
        
        # Remover hífens para padronização
        codigo_sem_hifen = codigo.replace('-', '')
        
        if codigo != codigo_sem_hifen:
            logger.info(f"Código normalizado: '{codigo}' -> '{codigo_sem_hifen}'")
        
        # Validar código sem hífens
        if not validar_codigo_infracao(codigo_sem_hifen):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de código inválido. Use o formato XXXX-X ou XXXXX"
            )

        # Usar o código sem hífen na consulta
        sql = f"{SQL_SELECT_INFRACOES} WHERE \"Código de Infração\" = :codigo LIMIT 1"
        result = db.execute(text(sql), {"codigo": codigo_sem_hifen})
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Infração com código {codigo_original} não encontrada"
            )
        
        # Resto do código continua igual...
        
        # Adiciona cache headers para resultados individuais
        response.headers["Cache-Control"] = f"public, max-age={CACHE_TTL_DETALHE}"
        response.headers["Vary"] = "Accept-Encoding"
        
        infracao = converter_row_objeto(row)
        registrar_metrica(request, inicio, "obter_infracao")
        return infracao

    except SQLAlchemyError as e:
        logger.error(f"Erro ao buscar infração {codigo}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erro ao acessar o banco de dados. Por favor, tente novamente mais tarde."
        )
    except HTTPException as e:
        logger.error(f"Erro de validação ao buscar infração {codigo}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar infração {codigo}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor. Por favor, tente novamente mais tarde."
        )

@router.post(
    "/",
    response_model=InfracaoSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova infração",
    description="Cria uma nova infração de trânsito no banco de dados.",
    responses={
        201: {
            "description": "Infração criada com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "codigo": "99999",
                        "descricao": "Nova infração de trânsito",
                        "responsavel": "Condutor",
                        "valor_multa": 195.23,
                        "orgao_autuador": "DETRAN",
                        "artigos_ctb": "244",
                        "pontos": 4,
                        "gravidade": "Média"
                    }
                }
            }
        },
        400: {
            "description": "Dados inválidos",
            "content": {
                "application/json": {
                    "example": {"detail": "Código da infração já existe"}
                }
            }
        },
        409: {
            "description": "Conflito - Infração já existe",
            "content": {
                "application/json": {
                    "example": {"detail": "Infração com código 99999 já existe"}
                }
            }
        }
    }
)
def criar_infracao(
    request: Request,
    infracao: InfracaoSchema,
    db: Session = Depends(get_db)
):
    """Cria uma nova infração no banco de dados."""
    inicio = time.time()
    
    try:
        # Validar dados
        validar_dados_infracao(infracao)
        
        # Verificar se já existe
        existing = db.query(InfracaoModel).filter(
            InfracaoModel.codigo == infracao.codigo
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Infração com código {infracao.codigo} já existe"
            )
        
        # Criar nova infração
        nova_infracao = InfracaoModel(
            codigo=infracao.codigo,
            descricao=infracao.descricao,
            responsavel=infracao.responsavel,
            valor_multa=infracao.valor_multa,
            orgao_autuador=infracao.orgao_autuador,
            artigos_ctb=infracao.artigos_ctb,
            pontos=infracao.pontos,
            gravidade=infracao.gravidade
        )
        
        db.add(nova_infracao)
        db.commit()
        db.refresh(nova_infracao)
        
        # Limpar cache do search_service
        search_service.limpar_cache_palavras()
        
        logger.info(f"Nova infração criada: {infracao.codigo}")
        registrar_metrica(request, inicio, "criar_infracao")
        
        return converter_row_objeto(nova_infracao)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Erro no banco de dados ao criar infração: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erro ao acessar o banco de dados. Por favor, tente novamente mais tarde."
        )
    except Exception as e:
        logger.error(f"Erro inesperado ao criar infração: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor. Por favor, tente novamente mais tarde."
        )

@router.put(
    "/{codigo}",
    response_model=InfracaoSchema,
    summary="Atualizar infração",
    description="Atualiza uma infração existente no banco de dados.",
    responses={
        200: {
            "description": "Infração atualizada com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "codigo": "99999",
                        "descricao": "Infração atualizada",
                        "responsavel": "Condutor",
                        "valor_multa": 195.23,
                        "orgao_autuador": "DETRAN",
                        "artigos_ctb": "244",
                        "pontos": 4,
                        "gravidade": "Média"
                    }
                }
            }
        },
        404: {
            "description": "Infração não encontrada",
            "content": {
                "application/json": {
                    "example": {"detail": "Infração com código 99999 não encontrada"}
                }
            }
        }
    }
)
def atualizar_infracao(
    request: Request,
    codigo: str = Path(..., description="Código da infração a ser atualizada"),
    infracao: InfracaoSchema = None,
    db: Session = Depends(get_db)
):
    """Atualiza uma infração existente."""
    inicio = time.time()
    
    try:
        # Validar dados
        validar_dados_infracao(infracao)
        
        # Buscar infração existente
        existing = db.query(InfracaoModel).filter(
            InfracaoModel.codigo == codigo
        ).first()
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Infração com código {codigo} não encontrada"
            )
        
        # Atualizar campos
        existing.descricao = infracao.descricao
        existing.responsavel = infracao.responsavel
        existing.valor_multa = infracao.valor_multa
        existing.orgao_autuador = infracao.orgao_autuador
        existing.artigos_ctb = infracao.artigos_ctb
        existing.pontos = infracao.pontos
        existing.gravidade = infracao.gravidade
        
        db.commit()
        db.refresh(existing)
        
        # Limpar cache do search_service
        search_service.limpar_cache_palavras()
        
        logger.info(f"Infração atualizada: {codigo}")
        registrar_metrica(request, inicio, "atualizar_infracao")
        
        return converter_row_objeto(existing)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Erro no banco de dados ao atualizar infração: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erro ao acessar o banco de dados. Por favor, tente novamente mais tarde."
        )
    except Exception as e:
        logger.error(f"Erro inesperado ao atualizar infração: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor. Por favor, tente novamente mais tarde."
        )

@router.delete(
    "/{codigo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar infração",
    description="Remove uma infração do banco de dados.",
    responses={
        204: {
            "description": "Infração deletada com sucesso"
        },
        404: {
            "description": "Infração não encontrada",
            "content": {
                "application/json": {
                    "example": {"detail": "Infração com código 99999 não encontrada"}
                }
            }
        }
    }
)
def deletar_infracao(
    request: Request,
    codigo: str = Path(..., description="Código da infração a ser deletada"),
    db: Session = Depends(get_db)
):
    """Deleta uma infração do banco de dados."""
    inicio = time.time()
    
    try:
        # Buscar infração existente
        existing = db.query(InfracaoModel).filter(
            InfracaoModel.codigo == codigo
        ).first()
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Infração com código {codigo} não encontrada"
            )
        
        # Deletar infração
        db.delete(existing)
        db.commit()
        
        # Limpar cache do search_service
        search_service.limpar_cache_palavras()
        
        logger.info(f"Infração deletada: {codigo}")
        registrar_metrica(request, inicio, "deletar_infracao")
        
        return None
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Erro no banco de dados ao deletar infração: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erro ao acessar o banco de dados. Por favor, tente novamente mais tarde."
        )
    except Exception as e:
        logger.error(f"Erro inesperado ao deletar infração: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor. Por favor, tente novamente mais tarde."
        )