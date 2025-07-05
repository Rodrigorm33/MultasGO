import os
import sys
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
    
    # Configuração de DEBUG
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Configurações do banco de dados (padrão SQLite local)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./multasgo.db")
    
    # Configurações de segurança
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    
    # ALLOWED_HOSTS configurado para desenvolvimento local e Cloudflare
    ALLOWED_HOSTS: list = os.getenv(
        "ALLOWED_HOSTS", 
        "localhost,127.0.0.1,*.cfargotunnel.com"
    ).split(",")
    
    # Configurações de busca fuzzy
    FUZZY_SEARCH_THRESHOLD: int = int(os.getenv("FUZZY_SEARCH_THRESHOLD", "70"))  # Limiar de similaridade (0-100)
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "20"))  # Número máximo de resultados

    # Configuração CORS (Cross-Origin Resource Sharing)
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Configuração de porta
    PORT: int = int(os.getenv("PORT", "8080"))
    
    def __init__(self):
        # Verificar se SECRET_KEY está definida
        if not self.SECRET_KEY:
            if self.DEBUG:
                # Em ambiente de desenvolvimento, usar uma chave temporária
                self.SECRET_KEY = "dev_temp_key_apenas_para_desenvolvimento"
                import warnings
                warnings.warn(
                    "AVISO: Usando uma SECRET_KEY temporária para desenvolvimento. "
                    "Defina SECRET_KEY nas variáveis de ambiente para um ambiente seguro.",
                    UserWarning
                )
            else:
                # Em ambiente de produção, exigir uma SECRET_KEY
                print("ERRO CRÍTICO: SECRET_KEY não está definida nas variáveis de ambiente!")
                print("Por motivos de segurança, a aplicação não pode iniciar sem uma SECRET_KEY em ambiente de produção.")
                sys.exit(1)

settings = Settings()