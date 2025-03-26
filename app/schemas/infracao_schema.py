from pydantic import BaseModel, Field
from typing import Optional, List

class InfracaoSchema(BaseModel):
    """Schema Pydantic para infrações de trânsito"""
    codigo: str = Field(..., description="Código da infração")
    descricao: str = Field(..., description="Descrição da infração")
    responsavel: str = Field(..., description="Responsável pela infração")
    valor_multa: float = Field(..., description="Valor da multa em reais")
    orgao_autuador: str = Field(..., description="Órgão responsável pela autuação")
    artigos_ctb: str = Field(..., description="Artigos do Código de Trânsito Brasileiro")
    pontos: int = Field(..., description="Pontos na carteira")
    gravidade: str = Field(..., description="Gravidade da infração")

    def get(self, key, default=None):
        """Método para compatibilidade com dicionários."""
        if hasattr(self, key):
            return getattr(self, key)
        return default

    def __getitem__(self, key):
        """Permite acessar propriedades do objeto usando a notação de dicionário."""
        return getattr(self, key)

    class Config:
        from_attributes = True
        json_schema_extra = {
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

class InfracaoPesquisaResponse(BaseModel):
    """Schema para resposta de pesquisa de infrações"""
    resultados: List[InfracaoSchema] = Field(default_factory=list, description="Lista de infrações encontradas")
    total: int = Field(0, description="Total de infrações encontradas")
    mensagem: Optional[str] = Field(None, description="Mensagem informativa sobre a pesquisa")
    sugestao: Optional[str] = Field(None, description="Sugestão de termo similar, se houver")

    class Config:
        json_schema_extra = {
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
                "mensagem": None,
                "sugestao": None
            }
        }

class InfracaoPesquisaParams(BaseModel):
    """Schema para parâmetros de pesquisa"""
    query: str = Field(..., description="Termo de pesquisa (código ou descrição)")
    limit: Optional[int] = Field(10, description="Número máximo de resultados")
    skip: Optional[int] = Field(0, description="Número de resultados para pular")