from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlalchemy
import time
import os
from sqlalchemy.exc import OperationalError, DatabaseError

from app.core.config import settings
from app.core.logger import logger

# Função para tentar conectar ao banco de dados com retry
def create_db_engine_with_retry(max_retries=10, retry_interval=5):
    retry_count = 0
    last_exception = None
    
    # Exibir informações de diagnóstico
    logger.info(f"Python version: {os.sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Environment variables: {[k for k in os.environ.keys()]}")
    logger.info(f"PORT environment variable: {os.environ.get('PORT', 'not set')}")
    
    # Verificar variáveis de ambiente do PostgreSQL
    pg_vars = {
        'PGUSER': os.environ.get('PGUSER', 'not set'),
        'PGHOST': os.environ.get('PGHOST', 'not set'),
        'PGPORT': os.environ.get('PGPORT', 'not set'),
        'PGDATABASE': os.environ.get('PGDATABASE', 'not set')
    }
    logger.info(f"PostgreSQL environment variables: {pg_vars}")
    
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
                echo=settings.DEBUG, # Mostra SQL apenas em modo debug
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "multasgo",
                    "keepalives": 1,
                    "keepalives_idle": 5,
                    "keepalives_interval": 2,
                    "keepalives_count": 3
                }
            )
            
            # Testar a conexão
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info(f"Conexão com o banco de dados estabelecida e testada com sucesso: {result.fetchone()}")
                
                # Verificar se a tabela autos existe
                try:
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'autos'
                        )
                    """))
                    if result.fetchone()[0]:
                        logger.info("Tabela 'autos' encontrada no banco de dados")
                        # Verificar quantidade de registros
                        count_result = conn.execute(text("SELECT COUNT(*) FROM autos"))
                        count = count_result.fetchone()[0]
                        logger.info(f"Total de registros na tabela autos: {count}")
                    else:
                        logger.warning("Tabela 'autos' NÃO encontrada no banco de dados")
                except Exception as e:
                    logger.warning(f"Erro ao verificar tabela 'autos': {e}")
                
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
    # Não levante a exceção, apenas registre o erro e continue
    # Isso permite que a aplicação inicie mesmo sem banco de dados
    # e exiba uma mensagem de erro apropriada
    engine = None

# Sessão do SQLAlchemy
if engine:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # Criar uma sessão fictícia que sempre levantará exceção quando usada
    logger.warning("Criando sessão fictícia devido a falha na conexão com o banco de dados")
    SessionLocal = None

# Base para os modelos
Base = declarative_base()

# Função para obter uma sessão do banco de dados
def get_db():
    if SessionLocal is None:
        logger.error("Tentativa de obter sessão de banco de dados, mas a conexão falhou na inicialização")
        raise Exception("Conexão com o banco de dados não está disponível")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()