from sqlalchemy import Column, Integer, String, Float, Text
from sqlalchemy.dialects.postgresql import TEXT
from app.db.database import Base
from pydantic import BaseModel, Field

class InfracaoBase(Base):
    """
    Modelo para representar uma infração de trânsito.
    """
    __tablename__ = "bdbautos"
    
    codigo = Column("Código de Infração", String(50), primary_key=True)
    descricao = Column("Infração", String(500), nullable=False)
    responsavel = Column("Responsável", String(100), nullable=False)
    valor_multa = Column("Valor da Multa", Float, nullable=False)
    orgao_autuador = Column("Órgão Autuador", String(100), nullable=False)
    artigos_ctb = Column("Artigos do CTB", String(100), nullable=False)
    pontos = Column("pontos", Integer, nullable=False)
    gravidade = Column("gravidade", String(50), nullable=False)
    
    def __repr__(self):
        return f"<Infracao(codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"

class Infracao(BaseModel):
    codigo: str = Field(description="Código da infração")
    descricao: str = Field(description="Descrição da infração")
    responsavel: str = Field(description="Responsável pela infração")
    valor_multa: float = Field(description="Valor da multa")
    orgao_autuador: str = Field(description="Órgão autuador")
    artigos_ctb: str = Field(description="Artigos do CTB")
    pontos: int = Field(description="Pontos da infração")
    gravidade: str = Field(description="Gravidade da infração")