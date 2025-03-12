from pydantic import BaseModel, Field
from typing import Optional, List

class InfracaoBase(BaseModel):
    """Esquema base para infrações de trânsito"""
    codigo: str = Field(..., description="Código da infração")
    descricao: str = Field(..., description="Descrição da infração")
    responsavel: str = Field(..., description="Responsável pela infração")
    valor_multa: float = Field(..., description="Valor da multa em reais")
    orgao_autuador: str = Field(..., description="Órgão responsável pela autuação")
    artigos_ctb: str = Field(..., description="Artigos do Código de Trânsito Brasileiro")
    pontos: int = Field(..., description="Pontos na carteira")
    gravidade: str = Field(..., description="Gravidade da infração")

    class Config:
        from_attributes = True

class InfracaoResponse(InfracaoBase):
    """Esquema para resposta da API"""
    pass

class InfracaoPesquisaResponse(BaseModel):
    """Esquema para resposta de pesquisa de infrações"""
    resultados: List[InfracaoResponse] = Field(default_factory=list, description="Lista de infrações encontradas")
    total: int = Field(0, description="Total de infrações encontradas")
    mensagem: Optional[str] = None
    sugestao: Optional[str] = None

class InfracaoPesquisaParams(BaseModel):
    """Esquema para parâmetros de pesquisa"""
    query: str = Field(..., description="Termo de pesquisa (código ou descrição)")
    limit: Optional[int] = 10
    skip: Optional[int] = 0