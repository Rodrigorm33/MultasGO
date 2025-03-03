"""
Script para criar manualmente as tabelas no banco de dados.
Útil para execução direta quando as tabelas não são criadas automaticamente.
"""
import sys
import os

# Adicionar o diretório raiz ao path para importar os módulos da aplicação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import create_engine, inspect
from app.core.config import settings
from app.core.logger import logger
from app.db.database import Base
from app.models.infracao import Infracao  # Importar todos os modelos necessários

def create_tables():
    """
    Cria as tabelas no banco de dados.
    """
    try:
        # Criar engine de conexão
        engine = create_engine(settings.DATABASE_URL)
        
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
        else:
            print("Nenhuma nova tabela foi criada.")
        
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