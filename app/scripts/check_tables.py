from sqlalchemy import create_engine, inspect
from app.core.config import settings
from app.core.logger import logger

def check_tables():
    try:
        # Criar engine de conexão
        engine = create_engine(settings.DATABASE_URL)
        
        # Inspecionar o banco de dados
        inspector = inspect(engine)
        
        # Listar todas as tabelas
        tables = inspector.get_table_names()
        
        if tables:
            logger.info(f"Tabelas encontradas no banco de dados: {tables}")
        else:
            logger.warning("Nenhuma tabela encontrada no banco de dados.")
        
        return tables
    except Exception as e:
        logger.error(f"Erro ao verificar as tabelas: {e}")
        return []

if __name__ == "__main__":
    tables = check_tables()
    if tables:
        print(f"Tabelas encontradas no banco de dados: {tables}")
    else:
        print("Nenhuma tabela encontrada no banco de dados.")
