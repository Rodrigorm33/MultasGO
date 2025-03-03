"""
Script para criar manualmente as tabelas no banco de dados.
Útil para execução direta quando as tabelas não são criadas automaticamente.
"""
import sys
import os
import time

# Adicionar o diretório raiz ao path para importar os módulos da aplicação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from app.core.config import settings
from app.core.logger import logger
from app.db.database import Base
from app.models.infracao import Infracao  # Importar todos os modelos necessários

def test_connection(url, max_retries=5, retry_interval=2):
    """
    Testa a conexão com o banco de dados com tentativas de reconexão.
    """
    engine = None
    for attempt in range(max_retries):
        try:
            print(f"Tentativa {attempt + 1} de {max_retries} para conectar ao banco de dados...")
            # Criar engine com timeout curto para teste
            engine = create_engine(
                url, 
                connect_args={
                    "connect_timeout": 5,
                    "application_name": "multasgo_create_tables"
                }
            )
            # Testar conexão
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print(f"Conexão bem-sucedida! Resultado: {result.fetchone()}")
                return engine
        except Exception as e:
            print(f"Erro na tentativa {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Aguardando {retry_interval} segundos antes de tentar novamente...")
                time.sleep(retry_interval)
            else:
                print("Todas as tentativas de conexão falharam.")
                raise
    return None

def create_tables():
    """
    Cria as tabelas no banco de dados.
    """
    try:
        # Exibir informações de diagnóstico
        print(f"DATABASE_URL: {settings.DATABASE_URL.split('@')[0].split(':')[0]}:***@{settings.DATABASE_URL.split('@')[1]}")
        print(f"Variáveis de ambiente PG_*:")
        print(f"  PGUSER: {os.environ.get('PGUSER', 'não definido')}")
        print(f"  PGHOST: {os.environ.get('PGHOST', 'não definido')}")
        print(f"  PGPORT: {os.environ.get('PGPORT', 'não definido')}")
        print(f"  PGDATABASE: {os.environ.get('PGDATABASE', 'não definido')}")
        
        # Testar conexão com o banco de dados
        print("Testando conexão com o banco de dados...")
        engine = test_connection(settings.DATABASE_URL)
        
        if not engine:
            print("Não foi possível conectar ao banco de dados.")
            return False
        
        # Verificar tabelas existentes
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        print(f"Tabelas existentes antes da criação: {existing_tables}")
        
        # Criar todas as tabelas
        print("Criando tabelas...")
        Base.metadata.create_all(bind=engine)
        
        # Verificar tabelas após criação
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()
        print(f"Tabelas após criação: {new_tables}")
        
        # Verificar se as tabelas foram criadas
        if len(new_tables) > len(existing_tables):
            print(f"Sucesso! {len(new_tables) - len(existing_tables)} novas tabelas criadas.")
            # Listar as novas tabelas
            new_table_names = set(new_tables) - set(existing_tables)
            print(f"Novas tabelas: {new_table_names}")
        else:
            print("Nenhuma nova tabela foi criada.")
            if 'autos' in new_tables:
                print("A tabela 'autos' já existe no banco de dados.")
            else:
                print("AVISO: A tabela 'autos' NÃO existe no banco de dados!")
        
        # Verificar se há dados na tabela autos
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM autos"))
                count = result.fetchone()[0]
                print(f"Total de registros na tabela autos: {count}")
        except Exception as e:
            print(f"Erro ao verificar registros na tabela autos: {e}")
        
        return True
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando criação manual de tabelas...")
    success = create_tables()
    if success:
        print("Processo concluído com sucesso!")
    else:
        print("Processo concluído com erros. Verifique os logs.")
        sys.exit(1) 