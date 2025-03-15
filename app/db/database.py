import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import psycopg2
import psycopg2.extensions
from psycopg2.extras import register_default_json, register_default_jsonb
from urllib.parse import urlparse

from app.core.config import settings
from app.core.logger import logger

# Registros de tipos do PostgreSQL
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

# Definição dos tipos de dados
TEXT_OID, NUMERIC_OID, VARCHAR_OID = 25, 1700, 1043
INT_OID, FLOAT_OID, BOOL_OID = 23, 701, 16

def process_database_url(db_url):
    try:
        # Verificar se estamos usando a URL pública do Railway
        if 'ballast.proxy.rlwy.net' in db_url:
            logger.info("Usando conexão remota com banco de dados do Railway via URL pública")
            return db_url
        
        # Usar variáveis de ambiente do Railway (para ambiente de produção)
        host = os.getenv('PGHOST', settings.PGHOST)
        port = os.getenv('PGPORT', settings.PGPORT)
        user = os.getenv('PGUSER', settings.PGUSER)
        password = os.getenv('PGPASSWORD', settings.PGPASSWORD)
        database = os.getenv('PGDATABASE', settings.PGDATABASE)

        # Log de segurança (sem mostrar senha)
        logger.info(f"Configurações de conexão - Host: {host}, Porta: {port}, Usuário: {user}, Database: {database}")

        # Construir URL segura
        safe_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        return safe_url
    
    except Exception as e:
        logger.error(f"Erro ao processar URL do banco de dados: {e}")
        return None

# Registrar adaptadores para tipos específicos
psycopg2.extensions.register_type(
    psycopg2.extensions.new_type((TEXT_OID,), 'TEXT', 
    lambda value, cursor: value)
)
psycopg2.extensions.register_type(
    psycopg2.extensions.new_type((NUMERIC_OID,), 'NUMERIC', 
    lambda value, cursor: float(value) if value is not None else None)
)

# Registro de JSON
register_default_json()
register_default_jsonb()

# Criação do engine
try:
    # Processar a URL do banco de dados
    processed_url = process_database_url(settings.DATABASE_URL)
    
    if not processed_url:
        raise ValueError("Não foi possível processar a URL do banco de dados")
    
    # Criar engine com opções otimizadas
    engine = create_engine(
        processed_url,
        echo=settings.DEBUG,  # Mostrar SQL no console se DEBUG for True
        future=True,  # Usar recursos futuros do SQLAlchemy
        pool_pre_ping=True,  # Verificar conexão antes de usar
        pool_recycle=3600,  # Reciclar conexões após 1 hora
        pool_size=10,  # Tamanho do pool de conexões
        max_overflow=20,  # Número máximo de conexões extras
        connect_args={
            'options': '-c timezone=UTC',  # Definir timezone para UTC
            'client_encoding': 'utf8'  # Usar UTF-8 para codificação
        }
    )
    logger.info("Conexão com o banco de dados estabelecida com sucesso")

except Exception as e:
    logger.error(f"Erro crítico ao configurar banco de dados: {e}")
    
    # Fallback para SQLite em memória
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    logger.warning("Usando banco de dados SQLite em memória como fallback")

# Configuração da sessão
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# Base para modelos
Base = declarative_base()

# Função para obter sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Erro na sessão do banco de dados: {e}")
        db.rollback()
    finally:
        db.close()