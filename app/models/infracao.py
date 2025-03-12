from sqlalchemy import Column, Integer, String, Float, Text
from app.db.database import Base

class Infracao(Base):
    """
    Modelo para representar uma infração de trânsito.
    """
    __tablename__ = "bdbautos"
    
    # Usar aliases para todas as colunas
    codigo = Column("Código de Infração", String(10), primary_key=True)
    descricao = Column("Infração", Text, nullable=False)
    responsavel = Column("Responsável", String(50), nullable=False)
    valor_multa = Column("Valor da Multa", Float, nullable=False)
    orgao_autuador = Column("Órgão Autuador", String(100), nullable=False)
    artigos_ctb = Column("Artigos do CTB", String(100), nullable=False)
    pontos = Column("pontos", Integer, nullable=False)
    gravidade = Column("gravidade", String(20), nullable=False)
    
    # Manter id para compatibilidade, mas como não-primário
    id = Column(Integer, autoincrement=True, nullable=True)
    
    def __repr__(self):
        return f"<Infracao(codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"