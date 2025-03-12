from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects import postgresql

from app.core.config import settings
from app.core.logger import logger

# Criação do engine do SQLAlchemy com configurações específicas para PostgreSQL
try:
    # Adicionando opções para lidar com tipos específicos do PostgreSQL
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"options": "-c timezone=utc"},
        pool_pre_ping=True,
        json_serializer=lambda obj: obj
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