from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

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
        infracoes = db.query(Infracao).offset(skip).limit(limit).all()
        logger.info(f"Listagem de infrações: {len(infracoes)} registros retornados")
        return infracoes
    except Exception as e:
        logger.error(f"Erro ao listar infrações: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

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
        logger.info(f"Iniciando pesquisa com termo: '{query}'")
        resultados = pesquisar_infracoes(db, query, limit, skip)
        return resultados
    except Exception as e:
        logger.error(f"Erro ao pesquisar infrações: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@router.get("/{codigo}", response_model=InfracaoResponse)
def obter_infracao(codigo: str, db: Session = Depends(get_db)):
    """
    Retorna uma infração específica pelo código.
    
    - **codigo**: Código da infração
    """
    try:
        infracao = db.query(Infracao).filter(Infracao.codigo == codigo).first()
        if not infracao:
            logger.warning(f"Infração com código '{codigo}' não encontrada")
            raise HTTPException(status_code=404, detail=f"Infração com código {codigo} não encontrada")
        
        logger.info(f"Infração com código '{codigo}' encontrada")
        return infracao
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter infração com código '{codigo}': {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}") 