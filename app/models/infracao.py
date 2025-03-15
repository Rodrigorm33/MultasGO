from sqlalchemy import Column, Integer, String, Float, Text
from sqlalchemy.dialects.postgresql import TEXT
from app.db.database import Base
from pydantic import BaseModel, Field

class InfracaoBase(Base):
    """
    Modelo SQLAlchemy para representar uma infração de trânsito.
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
    codigo: str 
    descricao: str
    responsavel: str
    valor_multa: float
    orgao_autuador: str
    artigos_ctb: str
    pontos: int
    gravidade: str
    
    def get(self, key, default=None):
        """Método para compatibilidade com dicionários."""
        if hasattr(self, key):
            return getattr(self, key)
        return default

    def __getitem__(self, key):
        """
        Permite acessar propriedades do objeto usando a notação de dicionário.
        Por exemplo: infracao['codigo'] retornará o mesmo que infracao.codigo
        """
        return getattr(self, key)

    class Config:
        from_attributes = True