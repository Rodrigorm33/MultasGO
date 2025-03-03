from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlalchemy
import time
from sqlalchemy.exc import OperationalError, DatabaseError

from app.core.config import settings
from app.core.logger import logger

# Função para tentar conectar ao banco de dados com retry
def create_db_engine_with_retry(max_retries=5, retry_interval=5):
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            # Mostrar a versão do SQLAlchemy para debug
            logger.info(f"Versão do SQLAlchemy: {sqlalchemy.__version__}")
            
            # Mostrar parte da URL do banco de dados (sem credenciais)
            db_url_parts = settings.DATABASE_URL.split("@")
            if len(db_url_parts) > 1:
                safe_url = f"{db_url_parts[0].split(':')[0]}:***@{db_url_parts[1]}"
            else:
                safe_url = "***URL protegida***"
            
            logger.info(f"Tentativa {retry_count + 1} de conexão ao banco de dados: {safe_url}")
            
            # Configuração do engine com parâmetros para melhorar a estabilidade
            engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,  # Verifica a conexão antes de usar
                pool_recycle=300,    # Recicla conexões a cada 5 minutos
                pool_timeout=30,     # Timeout para obter uma conexão do pool
                max_overflow=10,     # Número máximo de conexões extras
                pool_size=5,         # Tamanho do pool de conexões
                echo=settings.DEBUG  # Mostra SQL apenas em modo debug
            )
            
            # Testar a conexão
            with engine.connect() as conn:
                conn.execute("SELECT 1")
                logger.info("Conexão com o banco de dados estabelecida e testada com sucesso")
                return engine
                
        except (OperationalError, DatabaseError) as e:
            last_exception = e
            retry_count += 1
            logger.warning(f"Falha na tentativa {retry_count} de conexão ao banco de dados: {e}")
            
            if retry_count < max_retries:
                logger.info(f"Tentando novamente em {retry_interval} segundos...")
                time.sleep(retry_interval)
            else:
                logger.error(f"Todas as {max_retries} tentativas de conexão falharam. Último erro: {e}")
                raise
        except Exception as e:
            logger.error(f"Erro inesperado ao conectar ao banco de dados: {e}")
            raise
    
    # Se chegou aqui, todas as tentativas falharam
    raise last_exception

# Criação do engine do SQLAlchemy com retry
try:
    engine = create_db_engine_with_retry()
except Exception as e:
    logger.error(f"Erro fatal ao conectar ao banco de dados: {e}")
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