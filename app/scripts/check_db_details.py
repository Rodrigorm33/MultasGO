"""
Script para verificar detalhes do banco de dados PostgreSQL.
"""
import sys
import os

# Adicionar o diretório raiz ao path para importar os módulos da aplicação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

def check_db_details():
    """
    Verifica detalhes do banco de dados PostgreSQL.
    """
    try:
        # Criar engine de conexão
        engine = create_engine(settings.DATABASE_URL)
        
        # Obter inspetor
        inspector = inspect(engine)
        
        # Obter informações do banco de dados
        with engine.connect() as conn:
            # Nome do banco de dados atual
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"Banco de dados atual: {db_name}")
            
            # Esquemas disponíveis
            result = conn.execute(text("SELECT schema_name FROM information_schema.schemata"))
            schemas = [row[0] for row in result]
            print(f"Esquemas disponíveis: {schemas}")
            
            # Tabelas em cada esquema
            for schema in schemas:
                tables = inspector.get_table_names(schema=schema)
                print(f"Tabelas no esquema '{schema}': {tables}")
            
            # Verificar tabela 'infracoes' em todos os esquemas
            for schema in schemas:
                result = conn.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = '{schema}' AND table_name = 'infracoes')"))
                exists = result.scalar()
                if exists:
                    print(f"A tabela 'infracoes' existe no esquema '{schema}'")
                    
                    # Contar registros
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.infracoes"))
                    count = result.scalar()
                    print(f"Número de registros na tabela '{schema}.infracoes': {count}")
            
            # Verificar usuários e permissões
            result = conn.execute(text("SELECT usename FROM pg_user"))
            users = [row[0] for row in result]
            print(f"Usuários do banco de dados: {users}")
            
            # Verificar conexões ativas
            result = conn.execute(text("SELECT count(*) FROM pg_stat_activity"))
            connections = result.scalar()
            print(f"Conexões ativas: {connections}")
            
        return True
    except Exception as e:
        print(f"Erro ao verificar detalhes do banco de dados: {e}")
        return False

if __name__ == "__main__":
    print("Verificando detalhes do banco de dados...")
    success = check_db_details()
    if success:
        print("Verificação concluída com sucesso!")
    else:
        print("Verificação concluída com erros.")
        sys.exit(1) 