from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import psycopg2
import psycopg2.extensions

from app.core.config import settings
from app.core.logger import logger

# Registrar tipos adicionais do PostgreSQL
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

# Criação do engine do SQLAlchemy com configurações específicas para PostgreSQL
try:
    # Adicionando opções para lidar com tipos específicos do PostgreSQL
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,  # Não mostrar SQL no console
        future=True,  # Usar recursos futuros do SQLAlchemy
        pool_pre_ping=True,  # Verificar conexão antes de usar
        pool_recycle=3600,  # Reciclar conexões após 1 hora
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