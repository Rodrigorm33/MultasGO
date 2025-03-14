from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
import traceback

from app.db.database import get_db
from app.models.infracao import Infracao
from app.schemas.infracao import InfracaoResponse, InfracaoPesquisaResponse
from app.services.direct_search_service import pesquisar_infracoes
from app.core.logger import logger

router = APIRouter()

@router.get("/", response_model=List[InfracaoResponse])
def listar_infracoes(
    skip: int = Query(0, description="Número de registros para pular (paginação)"),
    limit: int = Query(100, description="Número máximo de registros para retornar"),
    db: Session = Depends(get_db)
):
    """
    Retorna uma lista de infrações de trânsito.
    
    - **skip**: Número de registros para pular (paginação)
    - **limit**: Número máximo de registros para retornar
    """
    try:
        logger.info(f"Listando infrações com skip={skip}, limit={limit}")
        
        # Usar o novo serviço de busca direta (com string vazia para listar tudo)
        resultado = pesquisar_infracoes("", limit=limit, skip=skip)
        
        # Converter para objetos Infracao para manter compatibilidade com o response_model
        infracoes = []
        for item in resultado["resultados"]:
            # Passar todos os valores durante a inicialização do objeto
            infracao = Infracao(
                codigo=item.get("Código de Infração", ""),
                descricao=item.get("Infração", ""),
                responsavel=item.get("Responsável", ""),
                valor_multa=item.get("Valor da Multa", "0"),
                orgao_autuador=item.get("Órgão Autuador", ""),
                artigos_ctb=item.get("Artigos do CTB", ""),
                pontos=item.get("pontos", "0"),
                gravidade=item.get("gravidade", "")
            )
            infracoes.append(infracao)
        
        logger.info(f"Listagem de infrações: {len(infracoes)} registros retornados")
        
        if not infracoes:
            logger.warning("Nenhuma infração encontrada")
            return []
            
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
            
        # Usar o novo serviço de busca direta
        resultado = pesquisar_infracoes(query, limit=limit, skip=skip)
        
        # Converter para objetos Infracao para manter compatibilidade com o response_model
        infracoes = []
        for item in resultado["resultados"]:
            # Passar todos os valores durante a inicialização do objeto
            infracao = Infracao(
                codigo=item.get("Código de Infração", ""),
                descricao=item.get("Infração", ""),
                responsavel=item.get("Responsável", ""),
                valor_multa=item.get("Valor da Multa", "0"),
                orgao_autuador=item.get("Órgão Autuador", ""),
                artigos_ctb=item.get("Artigos do CTB", ""),
                pontos=item.get("pontos", "0"),
                gravidade=item.get("gravidade", "")
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
        if resultado.get('sugestao'):
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
        
        # Usar o novo serviço de busca direta
        resultado = pesquisar_infracoes(codigo, limit=1)
        
        if resultado["total"] == 0:
            logger.warning(f"Infração com código '{codigo}' não encontrada")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Infração com código {codigo} não encontrada"
            )
        
        # Converter para objeto Infracao
        item = resultado["resultados"][0]
        infracao = Infracao(
            codigo=item.get("Código de Infração", ""),
            descricao=item.get("Infração", ""),
            responsavel=item.get("Responsável", ""),
            valor_multa=item.get("Valor da Multa", "0"),
            orgao_autuador=item.get("Órgão Autuador", ""),
            artigos_ctb=item.get("Artigos do CTB", ""),
            pontos=item.get("pontos", "0"),
            gravidade=item.get("gravidade", "")
        )
        
        logger.info(f"Infração com código '{codigo}' encontrada")
        return infracao
    except HTTPException:
        raise
    except Exception as e:
        error_detail = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Erro ao obter infração com código '{codigo}': {error_detail}")
        logger.error(f"Stack trace: {stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Erro ao obter infração com código {codigo}",
                "error": error_detail,
                "type": type(e).__name__
            }
        )