from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import psycopg2
import psycopg2.extensions
from psycopg2.extras import register_default_json, register_default_jsonb

from app.core.config import settings
from app.core.logger import logger

# Registrar tipos adicionais do PostgreSQL
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

# Registrar tipos específicos do PostgreSQL que podem causar problemas
# Tipo 25 é TEXT no PostgreSQL
TEXT_OID = 25
NUMERIC_OID = 1700
VARCHAR_OID = 1043
INT_OID = 23
FLOAT_OID = 701
BOOL_OID = 16

# Criar adaptadores personalizados para tipos problemáticos
class TextAdapter:
    def __init__(self, value):
        self.value = str(value) if value is not None else None
        
    def getquoted(self):
        if self.value is None:
            return 'NULL'
        return psycopg2.extensions.QuotedString(self.value).getquoted()

# Registrar adaptadores para tipos específicos
psycopg2.extensions.register_type(psycopg2.extensions.new_type((TEXT_OID,), 'TEXT', lambda value, cursor: value))
psycopg2.extensions.register_type(psycopg2.extensions.new_type((NUMERIC_OID,), 'NUMERIC', lambda value, cursor: float(value) if value is not None else None))
psycopg2.extensions.register_type(psycopg2.extensions.new_type((VARCHAR_OID,), 'VARCHAR', lambda value, cursor: str(value) if value is not None else None))
psycopg2.extensions.register_type(psycopg2.extensions.new_type((INT_OID,), 'INTEGER', lambda value, cursor: int(value) if value is not None else None))
psycopg2.extensions.register_type(psycopg2.extensions.new_type((FLOAT_OID,), 'FLOAT', lambda value, cursor: float(value) if value is not None else None))
psycopg2.extensions.register_type(psycopg2.extensions.new_type((BOOL_OID,), 'BOOLEAN', lambda value, cursor: bool(value) if value is not None else None))

# Registrar adaptadores para JSON e JSONB
register_default_json()
register_default_jsonb()

# Criação do engine do SQLAlchemy com configurações específicas para PostgreSQL
try:
    # Adicionando opções para lidar com tipos específicos do PostgreSQL
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,  # Não mostrar SQL no console
        future=True,  # Usar recursos futuros do SQLAlchemy
        pool_pre_ping=True,  # Verificar conexão antes de usar
        pool_recycle=3600,  # Reciclar conexões após 1 hora
        connect_args={
            'options': '-c timezone=UTC',  # Definir timezone para UTC
            'client_encoding': 'utf8'  # Usar UTF-8 para codificação
        }
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