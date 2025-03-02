from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.infracao import Infracao
from app.schemas.infracao import InfracaoResponse, InfracaoPesquisaResponse, InfracaoPesquisaParams
from app.services.search_service import pesquisar_infracoes

router = APIRouter(
    prefix="/infracoes",
    tags=["infracoes"],
    responses={404: {"description": "Infração não encontrada"}},
)

@router.get("/pesquisa", response_model=InfracaoPesquisaResponse)
def pesquisar(
    query: str = Query(..., description="Termo de pesquisa (código ou descrição)"),
    limit: int = Query(10, description="Número máximo de resultados"),
    skip: int = Query(0, description="Número de resultados para pular"),
    db: Session = Depends(get_db)
):
    """
    Pesquisa infrações por código ou descrição.
    """
    params = InfracaoPesquisaParams(query=query, limit=limit, skip=skip)
    return pesquisar_infracoes(db, params.query, params.limit, params.skip)

@router.get("/{codigo}", response_model=InfracaoResponse)
def get_infracao(codigo: str, db: Session = Depends(get_db)):
    """
    Obtém uma infração pelo código.
    """
    # Remover hífen se existir
    codigo_limpo = codigo.replace("-", "")
    
    # Buscar a infração no banco de dados
    infracao = db.query(Infracao).filter(Infracao.codigo == codigo_limpo).first()
    
    if not infracao:
        raise HTTPException(status_code=404, detail=f"Infração com código {codigo} não encontrada")
    
    return infracao 