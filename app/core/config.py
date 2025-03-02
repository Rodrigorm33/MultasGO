import os
from dotenv import load_dotenv
from pathlib import Path

# Carrega as variáveis de ambiente do arquivo .env
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    # Informações da aplicação
    APP_NAME: str = os.getenv("APP_NAME", "MultasGO")
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "MultasGO")
    PROJECT_DESCRIPTION: str = os.getenv("PROJECT_DESCRIPTION", "API para pesquisa de autos de infração de trânsito")
    PROJECT_VERSION: str = os.getenv("PROJECT_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Configurações do banco de dados
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/multas_db")
    
    # Configurações de segurança
    SECRET_KEY: str = os.getenv("SECRET_KEY", "chave_secreta_padrao_nao_use_em_producao")
    ALLOWED_HOSTS: list = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    
    # Configurações de busca fuzzy
    FUZZY_SEARCH_THRESHOLD: int = int(os.getenv("FUZZY_SEARCH_THRESHOLD", "70"))  # Limiar de similaridade (0-100)
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "20"))  # Número máximo de resultados

settings = Settings()