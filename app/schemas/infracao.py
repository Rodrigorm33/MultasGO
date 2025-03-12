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

class InfracaoCreate(InfracaoBase):
    """Esquema para criação de infrações"""
    pass

class InfracaoUpdate(InfracaoBase):
    """Esquema para atualização de infrações"""
    pass

class Infracao(InfracaoBase):
    # Removendo o campo id
    # id: int
    
    class Config:
        orm_mode = True

class InfracaoResponse(Infracao):
    """Esquema para resposta da API"""
    pass

class InfracaoPesquisaResponse(BaseModel):
    """Esquema para resposta de pesquisa de infrações"""
    resultados: List[InfracaoResponse] = Field([], description="Lista de infrações encontradas")
    total: int = Field(0, description="Total de infrações encontradas")
    mensagem: Optional[str] = Field(None, description="Mensagem informativa ou de erro")
    sugestao: Optional[str] = Field(None, description="Sugestão de termo correto quando há erro de digitação")
    
    class Config:
        from_attributes = True

class InfracaoPesquisaParams(BaseModel):
    """Esquema para parâmetros de pesquisa"""
    query: str = Field(..., description="Termo de pesquisa (código ou descrição)")
    limit: Optional[int] = Field(10, description="Número máximo de resultados")
    skip: Optional[int] = Field(0, description="Número de resultados para pular (paginação)")
    
    class Config:
        from_attributes = True 