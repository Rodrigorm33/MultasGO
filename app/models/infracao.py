from sqlalchemy import Column, Integer, String, Float, Text
from app.db.database import Base

class Infracao(Base):
    """
    Modelo para representar uma infração de trânsito.
    Baseado nas colunas do arquivo CSV:
    - Código de infração
    - Infração
    - Responsável
    - Valor da multa
    - Órgão Autuador
    - Artigos do CTB
    - Pontos
    - Gravidade
    """
    __tablename__ = "bdbautos"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(10), index=True, nullable=False, comment="Código da infração")
    descricao = Column(Text, nullable=False, comment="Descrição da infração")
    responsavel = Column(String(50), nullable=False, comment="Responsável pela infração")
    valor_multa = Column(Float, nullable=False, comment="Valor da multa em reais")
    orgao_autuador = Column(String(100), nullable=False, comment="Órgão responsável pela autuação")
    artigos_ctb = Column(String(100), nullable=False, comment="Artigos do Código de Trânsito Brasileiro")
    pontos = Column(Integer, nullable=False, comment="Pontos na carteira")
    gravidade = Column(String(20), nullable=False, comment="Gravidade da infração")
    
    def __repr__(self):
        return f"<Infracao(codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>" 