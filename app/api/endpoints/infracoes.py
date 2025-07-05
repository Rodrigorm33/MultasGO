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
    
    return InfracaoSchema(
        codigo=str(codigo) if codigo else "",
        descricao=str(descricao) if descricao else "",
        responsavel=str(responsavel) if responsavel else "",
        valor_multa=valor_multa_float,
        orgao_autuador=str(orgao_autuador) if orgao_autuador else "",
        artigos_ctb=str(artigos_ctb) if artigos_ctb else "",
        pontos=pontos_int,
        gravidade=str(gravidade) if gravidade else ""
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
    return converter_row_para_schema(
        codigo=item.get("codigo", ""),
        descricao=item.get("descricao", ""),
        responsavel=item.get("responsavel", ""),
        valor_multa=item.get("valor_multa", 0.0),
        orgao_autuador=item.get("orgao_autuador", ""),
        artigos_ctb=item.get("artigos_ctb", ""),
        pontos=item.get("pontos", 0),
        gravidade=item.get("gravidade", "")
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
                        "orgao_autuador": "PRF",
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
                            "orgao_autuador": "PRF",
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
                        "orgao_autuador": "PRF",
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

# Esquema para os parâmetros do explorador
from typing import List, Optional
from pydantic import BaseModel, Field

class ExplorarParams(BaseModel):
    """Schema para parâmetros do explorador de infrações"""
    gravidade: Optional[str] = Field(None, description="Filtro por gravidade")
    responsavel: Optional[str] = Field(None, description="Filtro por responsável")
    pontos: Optional[int] = Field(None, description="Filtro por pontos")
    codigo: Optional[str] = Field(None, description="Filtro por código")
    descricao: Optional[str] = Field(None, description="Filtro por descrição")
    valor_multa_min: Optional[float] = Field(None, description="Valor mínimo da multa")
    valor_multa_max: Optional[float] = Field(None, description="Valor máximo da multa")
    orgao_autuador: Optional[str] = Field(None, description="Filtro por órgão autuador")
    artigos_ctb: Optional[str] = Field(None, description="Filtro por artigos CTB")
    orderby: Optional[str] = Field("codigo", description="Campo para ordenação")
    direction: Optional[str] = Field("asc", description="Direção da ordenação (asc ou desc)")
    skip: Optional[int] = Field(0, ge=0, description="Número de registros para pular")
    limit: Optional[int] = Field(100, gt=0, le=1000, description="Número máximo de registros")

@router.post(
    "/explorador",
    response_model=InfracaoPesquisaResponse,
    summary="Explorador de infrações",
    description="Permite filtrar e ordenar infrações por múltiplos critérios",
    responses={
        200: {
            "description": "Operação bem-sucedida",
            "content": {
                "application/json": {
                    "example": {
                        "resultados": [
                            {
                                "codigo": "5169-1",
                                "descricao": "Dirigir sob influência de álcool",
                                "responsavel": "Condutor",
                                "valor_multa": 2934.70,
                                "orgao_autuador": "PRF",
                                "artigos_ctb": "165",
                                "pontos": 7,
                                "gravidade": "Gravíssima"
                            }
                        ],
                        "total": 1,
                        "mensagem": None
                    }
                }
            }
        }
    }
)
async def explorar_infracoes(
    request: Request,
    params: ExplorarParams,
    db: Session = Depends(get_db)
):
    """
    Endpoint para explorar infrações com filtros e ordenação avançados.
    Permite filtrar por qualquer campo e ordenar em qualquer direção.
    """
    inicio = time.time()
    try:
        # Construir a cláusula WHERE dinamicamente
        where_clauses = []
        query_params = {}
        
        # Adicionar filtros dinâmicos conforme especificado
        if params.codigo:
            where_clauses.append("CAST(\"Código de Infração\" AS TEXT) LIKE :codigo")
            query_params["codigo"] = f"%{params.codigo}%"
            
        if params.descricao:
            where_clauses.append("UPPER(\"Infração\") LIKE UPPER(:descricao)")
            query_params["descricao"] = f"%{params.descricao}%"
            
        if params.responsavel:
            if params.responsavel != "Todos":
                where_clauses.append("UPPER(\"Responsável\") LIKE UPPER(:responsavel)")
                query_params["responsavel"] = f"%{params.responsavel}%"
                
        if params.valor_multa_min is not None:
            where_clauses.append("\"Valor da multa\" >= :valor_multa_min")
            query_params["valor_multa_min"] = params.valor_multa_min
            
        if params.valor_multa_max is not None:
            where_clauses.append("\"Valor da multa\" <= :valor_multa_max")
            query_params["valor_multa_max"] = params.valor_multa_max
            
        if params.orgao_autuador:
            if params.orgao_autuador != "Todos":
                # Para valores específicos do seletor, usar igualdade exata
                predefined_values = ["Municipal/Rodoviario", "Estadual/Rodoviario", "Estadual/Municipal/Rodoviario", "Estadual", "Rodoviario"]
                if params.orgao_autuador in predefined_values:
                    where_clauses.append("\"Órgão Autuador\" = :orgao_autuador")
                    query_params["orgao_autuador"] = params.orgao_autuador
                else:
                    # Para busca livre (caso futuro), usar LIKE
                    where_clauses.append("UPPER(\"Órgão Autuador\") LIKE UPPER(:orgao_autuador)")
                    query_params["orgao_autuador"] = f"%{params.orgao_autuador}%"
            
        if params.artigos_ctb:
            where_clauses.append("UPPER(\"Artigos do CTB\") LIKE UPPER(:artigos_ctb)")
            query_params["artigos_ctb"] = f"%{params.artigos_ctb}%"
            
        if params.pontos is not None:
            if params.pontos != 0:  # Se 0, considere como "Todos"
                where_clauses.append("\"Pontos\" = :pontos")
                query_params["pontos"] = params.pontos
                
        if params.gravidade:
            if params.gravidade != "Todas":
                # Tratamento especial para Gravíssima (capturar todas as variações)
                if params.gravidade == "Gravissima":
                    where_clauses.append("UPPER(\"Gravidade\") LIKE UPPER(:gravidade)")
                    query_params["gravidade"] = "Gravissima%"  # Captura Gravissima, Gravissima2X, etc.
                # Tratamento especial para Leve (capturar todas as variações)
                elif params.gravidade == "Leve":
                    where_clauses.append("UPPER(\"Gravidade\") LIKE UPPER(:gravidade)")
                    query_params["gravidade"] = "Leve%"  # Captura Leve, Leve50%, etc.
                # Para outros valores, busca exata
                else:
                    where_clauses.append("UPPER(\"Gravidade\") = UPPER(:gravidade)")
                    query_params["gravidade"] = params.gravidade
        
        # Construir a cláusula WHERE completa
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Mapear os nomes dos campos para os nomes das colunas na tabela
        column_mapping = {
            "codigo": "\"Código de Infração\"",
            "descricao": "\"Infração\"",
            "responsavel": "\"Responsável\"",
            "valor_multa": "\"Valor da multa\"",
            "orgao_autuador": "\"Órgão Autuador\"",
            "artigos_ctb": "\"Artigos do CTB\"",
            "pontos": "\"Pontos\"",
            "gravidade": "\"Gravidade\""
        }
        
        # Definir ordenação
        order_column = column_mapping.get(params.orderby, "\"Código de Infração\"")
        order_direction = "DESC" if params.direction.lower() == "desc" else "ASC"
        
        # Construir e executar a consulta SQL
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
        ORDER BY {order_column} {order_direction}
        LIMIT :limit OFFSET :skip
        """
        
        # Adicionar parâmetros de paginação
        query_params["limit"] = params.limit
        query_params["skip"] = params.skip
        
        # Executar a consulta
        result = db.execute(text(sql), query_params)
        
        # Processar resultados
        resultados, total = processar_resultados(result)
        
        # Contar o total real de registros (opcional, pode impactar performance)
        count_sql = f"""
        SELECT COUNT(*) as total
        FROM bdbautos 
        WHERE {where_clause}
        """
        count_result = db.execute(text(count_sql), query_params).first()
        total_count = count_result.total if count_result else total
        
        # Registrar métricas
        registrar_metrica(request, inicio, "explorar_infracoes")
        
        # Retornar resposta
        return {
            "resultados": resultados,
            "total": total_count,
            "mensagem": None if total > 0 else "Nenhuma infração encontrada com os filtros selecionados."
        }
        
    except SQLAlchemyError as e:
        logger.error(f"Erro no banco de dados ao explorar infrações: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erro ao acessar o banco de dados. Por favor, tente novamente mais tarde."
        )
    except Exception as e:
        logger.error(f"Erro inesperado ao explorar infrações: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor. Por favor, tente novamente mais tarde."
        )