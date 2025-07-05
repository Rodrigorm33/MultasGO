import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import traceback
from urllib.parse import urlparse

from app.core.config import settings
from app.core.logger import logger

def create_database_engine():
    """
    Cria engine do banco de dados baseado na URL configurada.
    Suporta PostgreSQL e SQLite automaticamente.
    """
    try:
        db_url = settings.DATABASE_URL
        logger.info(f"Configurando banco de dados: {db_url.split('://')[0]}")
        
        # Detectar tipo de banco pela URL
        if db_url.startswith('sqlite'):
            # Configuração para SQLite
            logger.info("Usando banco de dados SQLite")
            engine = create_engine(
                db_url,
                echo=settings.DEBUG,
                connect_args={"check_same_thread": False}
            )
            
        elif db_url.startswith('postgresql'):
            # Configuração para PostgreSQL (mantida para compatibilidade)
            logger.info("Usando banco de dados PostgreSQL")
            engine = create_engine(
                db_url,
                echo=settings.DEBUG,
                future=True,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=10,
                max_overflow=20,
                connect_args={
                    'options': '-c timezone=UTC',
                    'client_encoding': 'utf8'
                }
            )
        else:
            raise ValueError(f"Tipo de banco não suportado: {db_url}")
        
        # Testar a conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            
        logger.info("Conexão com o banco de dados estabelecida com sucesso")
        return engine
        
    except Exception as e:
        logger.critical(f"Erro ao configurar banco de dados: {e}")
        logger.critical(f"Detalhes: {traceback.format_exc()}")
        
        if settings.DEBUG:
            # Em modo DEBUG, usar SQLite em memória como fallback
            logger.warning("Usando SQLite em memória como fallback")
            return create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False}
            )
        else:
            # Em produção, encerrar aplicação
            logger.critical("Aplicação encerrada devido a erro de banco de dados")
            import sys
            sys.exit(1)

# Criar engine
engine = create_database_engine()

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