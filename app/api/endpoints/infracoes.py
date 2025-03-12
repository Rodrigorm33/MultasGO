from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import traceback

from app.db.database import get_db
from app.models.infracao import Infracao
from app.schemas.infracao import InfracaoResponse, InfracaoPesquisaResponse
from app.services.search_service import pesquisar_infracoes
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
        infracoes = db.query(Infracao).offset(skip).limit(limit).all()
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
            
        resultados = pesquisar_infracoes(db, query, limit, skip)
        
        logger.info(f"Pesquisa concluída. Total de resultados: {resultados.get('total', 0)}")
        if resultados.get('sugestao'):
            logger.info(f"Sugestão encontrada: '{resultados['sugestao']}'")
            
        return resultados
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
            
        infracao = db.query(Infracao).filter(Infracao.codigo == codigo).first()
        
        if not infracao:
            logger.warning(f"Infração com código '{codigo}' não encontrada")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Infração com código {codigo} não encontrada"
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