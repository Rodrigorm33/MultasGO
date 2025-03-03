"""
Script para importar manualmente os dados do CSV para o banco de dados.
Útil para execução direta quando a importação automática falha.
"""
import sys
import os

# Adicionar o diretório raiz ao path para importar os módulos da aplicação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.import_service import importar_csv_para_db
from app.scripts.check_tables import check_tables

def import_data():
    """
    Importa os dados do CSV para o banco de dados.
    """
    try:
        # Criar engine de conexão
        engine = create_engine(settings.DATABASE_URL)
        
        # Criar sessão
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Verificar tabelas antes da importação
        print("Verificando tabelas antes da importação...")
        tables_before = check_tables()
        
        # Caminho para o arquivo CSV
        csv_path = os.path.join(os.getcwd(), "dbautos.csv")
        
        # Verificar se o arquivo CSV existe
        if not os.path.exists(csv_path):
            print(f"Arquivo CSV não encontrado: {csv_path}")
            
            # Listar arquivos no diretório atual
            files = os.listdir(os.getcwd())
            print(f"Arquivos no diretório atual: {files}")
            
            # Perguntar ao usuário pelo caminho correto
            user_path = input("Digite o caminho completo para o arquivo CSV: ")
            if os.path.exists(user_path):
                csv_path = user_path
            else:
                print(f"Arquivo não encontrado: {user_path}")
                return False
        
        # Importar os dados
        print(f"Importando dados de: {csv_path}")
        registros_importados = importar_csv_para_db(db, csv_path, force_update=True)
        
        # Verificar resultado
        if registros_importados > 0:
            print(f"Sucesso! {registros_importados} registros importados.")
            
            # Verificar tabelas após importação
            tables_after = check_tables()
            print(f"Tabelas após importação: {tables_after}")
            
            return True
        else:
            print("Nenhum registro foi importado.")
            return False
    
    except Exception as e:
        print(f"Erro durante a importação: {e}")
        return False
    finally:
        # Fechar a sessão
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    print("Iniciando importação manual de dados...")
    success = import_data()
    if success:
        print("Processo concluído com sucesso!")
    else:
        print("Processo concluído com erros. Verifique os logs.")
        sys.exit(1) 