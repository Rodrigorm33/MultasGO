from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlalchemy

from app.core.config import settings
from app.core.logger import logger

# Criação do engine do SQLAlchemy
try:
    # Mostrar a versão do SQLAlchemy para debug
    logger.info(f"Versão do SQLAlchemy: {sqlalchemy.__version__}")
    
    # Mostrar parte da URL do banco de dados (sem credenciais)
    db_url_parts = settings.DATABASE_URL.split("@")
    if len(db_url_parts) > 1:
        safe_url = f"{db_url_parts[0].split(':')[0]}:***@{db_url_parts[1]}"
    else:
        safe_url = "***URL protegida***"
    
    logger.info(f"Conectando ao banco de dados: {safe_url}")
    
    # Simplificando a criação do engine
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Verifica a conexão antes de usar
        echo=settings.DEBUG  # Mostra SQL apenas em modo debug
    )
    logger.info("Conexão com o banco de dados estabelecida com sucesso")
except Exception as e:
    logger.error(f"Erro ao conectar ao banco de dados: {e}")
    raise

# Sessão do SQLAlchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()

# Função para obter uma sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()