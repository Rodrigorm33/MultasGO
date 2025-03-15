from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app.db.database import get_db
from app.models.infracao import Infracao
from app.schemas.infracao import InfracaoPesquisaResponse, InfracaoResponse
from app.services.search_service import pesquisar_infracoes
from app.core.logger import logger

import traceback

# Função auxiliar para acessar atributos com segurança
def _get_attr_safe(obj, attr, default=None):
    """
    Função auxiliar para acessar atributos de objetos ou chaves de dicionários com segurança.
    Funciona tanto com objetos Infracao quanto com dicionários.
    """
    if obj is None:
        return default
    
    if isinstance(obj, dict):
        return obj.get(attr, default)
    elif hasattr(obj, attr):
        return getattr(obj, attr, default)
    else:
        return default


# Função auxiliar para converter objetos Infracao em dicionários
def _converter_para_dict(obj):
    """
    Converte um objeto Infracao em um dicionário.
    """
    if obj is None:
        return {}
    
    if isinstance(obj, dict):
        return obj
    
    # Se for um objeto, converter para dicionário
    obj_dict = {}
    for attr in ["codigo", "descricao", "responsavel", "valor_multa", 
                "orgao_autuador", "artigos_ctb", "pontos", "gravidade"]:
        if hasattr(obj, attr):
            obj_dict[attr] = getattr(obj, attr)
    
    return obj_dict


# Função auxiliar para converter objetos Infracao em dicionários
def _converter_para_dict(obj):
    """
    Converte um objeto Infracao em um dicionário.
    """
    if obj is None:
        return {}
    
    if isinstance(obj, dict):
        return obj
    
    # Se for um objeto, converter para dicionário
    obj_dict = {}
    for attr in ["codigo", "descricao", "responsavel", "valor_multa", 
                "orgao_autuador", "artigos_ctb", "pontos", "gravidade"]:
        if hasattr(obj, attr):
            obj_dict[attr] = getattr(obj, attr)
    
    return obj_dict

router = APIRouter()

@router.get("/", response_model=List[InfracaoResponse])
def listar_infracoes(
    skip: int = Query(0, description="Número de registros para pular (paginação)"),
    limit: int = Query(100, description="Número máximo de registros para retornar"),
    db: Session = Depends(get_db)
):
    """
    Lista todas as infrações disponíveis.
    
    - **skip**: Número de registros para pular (paginação)
    - **limit**: Número máximo de registros para retornar
    
    Retorna uma lista de infrações ordenadas por código.
    """
    try:
        logger.info(f"Listando infrações com skip={skip}, limit={limit}")
        
        # Consulta SQL para obter infrações
        sql = """
        SELECT 
            "Código de Infração" as codigo,
            "Infração" as descricao,
            "Responsável" as responsavel,
            "Valor da Multa" as valor_multa,
            "Órgão Autuador" as orgao_autuador,
            "Artigos do CTB" as artigos_ctb,
            pontos,
            gravidade
        FROM bdbautos
        ORDER BY "Código de Infração"
        LIMIT :limit OFFSET :skip
        """
        
        result = db.execute(text(sql), {"limit": limit, "skip": skip})
        
        # Converter resultados para objetos Infracao
        infracoes = []
        for row in result:
            # Garantir que temos dados válidos
            try:
                valor_multa = float(row.valor_multa) if row.valor_multa else 0.0
            except (ValueError, TypeError):
                valor_multa = 0.0

            try:
                pontos = int(float(row.pontos)) if row.pontos else 0
            except (ValueError, TypeError):
                pontos = 0

            # Criar objeto Infracao
            infracao = Infracao(
                codigo=str(row.codigo) if row.codigo else "",
                descricao=str(row.descricao) if row.descricao else "",
                responsavel=str(row.responsavel) if row.responsavel else "",
                valor_multa=valor_multa,
                orgao_autuador=str(row.orgao_autuador) if row.orgao_autuador else "",
                artigos_ctb=str(row.artigos_ctb) if row.artigos_ctb else "",
                pontos=pontos,
                gravidade=str(row.gravidade) if row.gravidade else ""
            )
            infracoes.append(infracao)

        logger.info(f"Listagem de infrações: {len(infracoes)} registros retornados")
        return infracoes
    except Exception as e:
        error_detail = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Erro ao listar infrações: {error_detail}")
        logger.error(f"Stack trace: {stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro ao listar infrações",
                "error": error_detail,
                "type": type(e).__name__
            }
        )

@router.get("/pesquisa", response_model=InfracaoPesquisaResponse)
def pesquisar(
    query: str = Query(..., description="Termo de pesquisa (código ou descrição da infração)"),
    skip: int = Query(0, description="Número de registros para pular (paginação)"),
    limit: int = Query(10, description="Número máximo de registros para retornar"),
    db: Session = Depends(get_db)
):
    """
    Pesquisa infrações por código ou descrição.
    
    - **query**: Termo de pesquisa (código ou descrição da infração)
    - **skip**: Número de registros para pular (paginação)
    - **limit**: Número máximo de registros para retornar
    
    A pesquisa suporta busca exata por código e busca fuzzy por descrição,
    permitindo encontrar resultados mesmo com erros de digitação.
    """
    try:
        logger.info(f"Iniciando pesquisa com termo: '{query}', skip={skip}, limit={limit}")
        
        if not query or len(query.strip()) < 2:
            logger.warning(f"Termo de pesquisa muito curto: '{query}'")
            return {
                "resultados": [],
                "total": 0,
                "mensagem": "O termo de pesquisa deve ter pelo menos 2 caracteres",
                "sugestao": None
            }
            
        # Usar o serviço de busca corrigido, passando o db como parâmetro
        resultado = pesquisar_infracoes(query, limit=limit, skip=skip, db=db)
        
        # Converter para objetos Infracao para manter compatibilidade com o response_model
        infracoes = []
        for item in resultado["resultados"]:
            try:
                # Garantir que temos dados válidos
                valor_multa = float(str(item.get("valor_multa", "0")).replace("R$", "").replace(".", "").replace(",", "."))
            except (ValueError, TypeError):
                valor_multa = 0.0

            try:
                pontos = int(float(str(item.get("pontos", "0"))))
            except (ValueError, TypeError):
                pontos = 0
            
            infracao = Infracao(
                codigo=str(item.get("codigo", "")),
                descricao=str(item.get("descricao", "")),
                responsavel=str(item.get("responsavel", "")),
                valor_multa=valor_multa,
                orgao_autuador=str(item.get("orgao_autuador", "")),
                artigos_ctb=str(item.get("artigos_ctb", "")),
                pontos=pontos,
                gravidade=str(item.get("gravidade", ""))
            )
            infracoes.append(infracao)
        
        # Preparar resposta no formato esperado pelo schema
        resposta = {
            "resultados": infracoes,
            "total": resultado["total"]
        }
        
        if "sugestao" in resultado:
            resposta["sugestao"] = resultado["sugestao"]
        
        if "mensagem" in resultado:
            resposta["mensagem"] = resultado["mensagem"]
        
        logger.info(f"Pesquisa concluída. Total de resultados: {resposta['total']}")
        if "sugestao" in resultado and resultado["sugestao"]:
            logger.info(f"Sugestão encontrada: '{resultado['sugestao']}'")
            
        return resposta
    except Exception as e:
        error_detail = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Erro ao pesquisar infrações: {error_detail}")
        logger.error(f"Stack trace: {stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro ao pesquisar infrações",
                "error": error_detail,
                "type": type(e).__name__,
                "query": query
            }
        )

@router.get("/{codigo}", response_model=InfracaoResponse)
def obter_infracao(codigo: str, db: Session = Depends(get_db)):
    """
    Retorna uma infração específica pelo código.
    
    - **codigo**: Código da infração
    """
    try:
        logger.info(f"Buscando infração com código: '{codigo}'")
        
        # Validar o código
        if not codigo or len(codigo.strip()) < 3:
            logger.warning(f"Código inválido: '{codigo}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Código de infração inválido: {codigo}. O código deve ter pelo menos 3 caracteres."
            )
        
        # Usar o serviço de busca com código como termo
        resultado = pesquisar_infracoes(codigo, limit=1, db=db)
        
        if resultado["total"] == 0:
            logger.warning(f"Infração com código '{codigo}' não encontrada")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Infração com código {codigo} não encontrada"
            )
        
        # Converter para objeto Infracao
        item = resultado["resultados"][0]
        
        # Converter para dicionário para evitar problemas com .get()
        item = _converter_para_dict(item)
        
        # Converter para dicionário para evitar problemas com .get()
        item = _converter_para_dict(item)
        
        # Garantir que item seja um dicionário
        if not isinstance(item, dict):
            # Se for um objeto, converter para dicionário
            item_dict = {}
            for attr in ["codigo", "descricao", "responsavel", "valor_multa", 
                        "orgao_autuador", "artigos_ctb", "pontos", "gravidade"]:
                if hasattr(item, attr):
                    item_dict[attr] = getattr(item, attr)
        else:
            item_dict = item
        
        # Extrair valores com segurança
        codigo = str(_get_attr_safe(item_dict, "codigo", ""))
        descricao = str(_get_attr_safe(item_dict, "descricao", ""))
        responsavel = str(_get_attr_safe(item_dict, "responsavel", ""))
        
        # Converter valor_multa para float
        try:
            valor_multa = float(_get_attr_safe(item_dict, "valor_multa", 0.0))
        except (ValueError, TypeError):
            valor_multa = 0.0
        
        orgao_autuador = str(_get_attr_safe(item_dict, "orgao_autuador", ""))
        artigos_ctb = str(_get_attr_safe(item_dict, "artigos_ctb", ""))
        
        # Converter pontos para int
        try:
            pontos = int(_get_attr_safe(item_dict, "pontos", 0))
        except (ValueError, TypeError):
            pontos = 0
        
        gravidade = str(_get_attr_safe(item_dict, "gravidade", ""))
        
        infracao = Infracao(
            codigo=codigo,
            descricao=descricao,
            responsavel=responsavel,
            valor_multa=valor_multa,
            orgao_autuador=orgao_autuador,
            artigos_ctb=artigos_ctb,
            pontos=pontos,
            gravidade=gravidade
        )
        
        logger.infologger.info(f"Infração com código '{codigo}' encontrada")
        return infracao
    except HTTPException:
        # Repassar exceções HTTP
        raise
    except Exception as e:
        error_detail = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Erro ao obter infração: {error_detail}")
        logger.error(f"Stack trace: {stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro ao obter infração",
                "error": error_detail,
                "type": type(e).__name__,
                "codigo": codigo
            }
        )
