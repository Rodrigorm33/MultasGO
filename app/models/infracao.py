from sqlalchemy import Column, Integer, String, Float, Text
from app.db.database import Base

class Infracao(Base):
    """
    Modelo para representar uma infração de trânsito.
    """
    __tablename__ = "bdbautos"
    
    # Usar codigo como chave primária (sem coluna id)
    codigo = Column("Código de Infração", String, primary_key=True)
    descricao = Column("Infração", String, nullable=False)
    responsavel = Column("Responsável", String, nullable=False)
    valor_multa = Column("Valor da Multa", Float, nullable=False)
    orgao_autuador = Column("Órgão Autuador", String, nullable=False)
    artigos_ctb = Column("Artigos do CTB", String, nullable=False)
    pontos = Column("pontos", Integer, nullable=False)
    gravidade = Column("gravidade", String, nullable=False)
    
    def __repr__(self):
        return f"<Infracao(codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"