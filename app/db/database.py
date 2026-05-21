import os
import time
from contextlib import contextmanager
from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
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
            # Configuração otimizada para SQLite
            logger.info("Usando banco de dados SQLite")

            # Configurações de performance para SQLite
            connect_args = {
                "check_same_thread": False,
                "timeout": 20,  # Timeout de 20 segundos
                "isolation_level": None,  # Autocommit mode
            }

            # Configurações específicas para produção
            if not settings.DEBUG:
                connect_args.update({
                    "timeout": 30,
                    "check_same_thread": False,
                })

            engine = create_engine(
                db_url,
                echo=settings.DEBUG,
                connect_args=connect_args,
                poolclass=StaticPool if ":memory:" in db_url else QueuePool,
                pool_size=settings.DB_POOL_SIZE if ":memory:" not in db_url else 1,
                max_overflow=settings.DB_MAX_OVERFLOW if ":memory:" not in db_url else 0,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_pre_ping=True,
                future=True
            )

            # Otimizações SQLite via eventos
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                """Configura otimizações SQLite para performance."""
                cursor = dbapi_connection.cursor()
                # Configurações de performance
                cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
                cursor.execute("PRAGMA synchronous=NORMAL")  # Balanço entre performance e segurança
                cursor.execute("PRAGMA cache_size=10000")  # Cache de 10MB
                cursor.execute("PRAGMA temp_store=MEMORY")  # Tabelas temporárias em memória
                cursor.execute("PRAGMA mmap_size=268435456")  # 256MB de memory mapping
                cursor.execute("PRAGMA optimize")  # Otimizações automáticas
                cursor.close()
            
        elif db_url.startswith('postgresql'):
            # Configuração otimizada para PostgreSQL
            logger.info("Usando banco de dados PostgreSQL")

            connect_args = {
                'options': '-c timezone=UTC',
                'client_encoding': 'utf8',
                'connect_timeout': 10,
                'application_name': 'MultasGO'
            }

            # Configurações específicas para produção
            if not settings.DEBUG:
                connect_args.update({
                    'connect_timeout': 30,
                    'command_timeout': 60,
                })

            engine = create_engine(
                db_url,
                echo=settings.DEBUG,
                future=True,
                pool_pre_ping=True,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                connect_args=connect_args,
                # Configurações de performance
                pool_timeout=30,
                pool_reset_on_return='commit',
                query_cache_size=1200
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
            fallback_engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )

            # Configurar pragma para fallback
            @event.listens_for(fallback_engine, "connect")
            def set_fallback_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=MEMORY")
                cursor.execute("PRAGMA synchronous=OFF")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.close()

            return fallback_engine
        else:
            # Em produção, encerrar aplicação
            logger.critical("Aplicação encerrada devido a erro de banco de dados")
            import sys
            sys.exit(1)

# Criar engine com tratamento de erro
try:
    engine = create_database_engine()
except Exception as e:
    logger.critical(f"Falha crítica ao inicializar banco de dados: {e}")
    if not settings.DEBUG:
        import sys
        sys.exit(1)
    else:
        # Em desenvolvimento, usar fallback
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )

# Configuração otimizada da sessão
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Melhora performance para objetos read-only
)

# Base para modelos
Base = declarative_base()

# Função otimizada para obter sessão do banco de dados
def get_db():
    """Generator para sessões do banco de dados com manejo de erro robusto."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Erro na sessão do banco de dados: {e}")
        db.rollback()
        raise  # Re-raise para permitir tratamento upstream
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Context manager para uso direto de sessões."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Erro na sessão do banco de dados: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def test_connection() -> bool:
    """Testa a conexão com o banco de dados."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Teste de conexão falhou: {e}")
        return False

def get_db_stats() -> dict:
    """Retorna estatísticas do pool de conexões."""
    try:
        pool = engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "invalid": pool.invalid(),
            "overflow": pool.overflow()
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do DB: {e}")
        return {}

def close_all_connections():
    """Fecha todas as conexões do pool (útil para shutdown graceful)."""
    try:
        engine.dispose()
        logger.info("Todas as conexões do banco foram fechadas")
    except Exception as e:
        logger.error(f"Erro ao fechar conexões: {e}")