from sqlalchemy import Column, Integer, String, Float, Text
from app.db.database import Base

class Infracao(Base):
    """
    Modelo para representar uma infração de trânsito.
    """
    __tablename__ = "bdbautos"
    
    # Não há coluna id, então vamos usar código como chave primária
    codigo = Column(String(10), primary_key=True, index=True, name="Código de infração")
    descricao = Column(Text, nullable=False, name="Infração")
    responsavel = Column(String(50), nullable=False, name="Responsável")
    valor_multa = Column(Float, nullable=False, name="Valor da Multa")
    orgao_autuador = Column(String(100), nullable=False, name="Órgão Autuador")
    artigos_ctb = Column(String(100), nullable=False, name="Artigos do CTB")
    pontos = Column(Integer, nullable=False, name="pontos")
    gravidade = Column(String(20), nullable=False, name="gravidade")
    
    # Precisamos adicionar um id já que o modelo espera um, mas que seja gerado pelo SQLAlchemy
    id = Column(Integer, primary_key=False, autoincrement=True, nullable=True)