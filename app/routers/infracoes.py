from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import re

from app.db.database import get_db
from app.models.infracao import Infracao
from app.schemas.infracao import InfracaoResponse, InfracaoPesquisaResponse, InfracaoPesquisaParams
from app.services.search_service import pesquisar_infracoes
from ..utils.rate_limiter import rate_limiter

router = APIRouter(
    prefix="/infracoes",
    tags=["infracoes"],
    responses={404: {"description": "Infração não encontrada"}},
)

def validate_query(query: str) -> bool:
    """Valida a query de pesquisa"""
    # Verificar tamanho
    if len(query) > 50:
        return False
    
    # Verificar caracteres e padrões suspeitos
    suspicious_patterns = [
        r'select\s+|insert\s+|update\s+|delete\s+|drop\s+|alter\s+',  # SQL
        r'<script|javascript:|alert\(|onclick|onerror',               # XSS
        r'\.\.\/|\.\.\\',                                            # Path Traversal
        r'\x00|\x1a|\x0d|\x0a',                                      # Null bytes
        r'^[!@#$%^&*(),.?":{}|<>]{3,}$'                             # Muitos caracteres especiais
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False
    
    return True

@router.get("/pesquisa", response_model=InfracaoPesquisaResponse)
async def pesquisar(request: Request, query: str = Query(..., description="Termo de pesquisa (código ou descrição)"),
    limit: int = Query(10, description="Número máximo de resultados"),
    skip: int = Query(0, description="Número de resultados para pular"),
    db: Session = Depends(get_db)
):
    """
    Pesquisa infrações por código ou descrição.
    """
    # Obter IP do cliente
    client_ip = request.client.host
    
    # Verificar rate limit
    can_proceed, wait_time = rate_limiter.check_rate_limit(client_ip)
    if not can_proceed:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas requisições. Por favor, aguarde {wait_time} segundos."
        )
    
    # Validar query
    if not validate_query(query):
        raise HTTPException(
            status_code=400,
            detail="Consulta inválida. Use apenas letras, números e caracteres simples."
        )
    
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