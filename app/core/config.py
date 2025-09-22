import os
import sys
import secrets
from typing import List
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

    # Configurações de segurança avançadas
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))  # Requests por minuto
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # Janela em segundos
    BLOCK_DURATION: int = int(os.getenv("BLOCK_DURATION", "300"))  # Tempo de bloqueio (5 min)
    MAX_REQUEST_SIZE: int = int(os.getenv("MAX_REQUEST_SIZE", str(1024 * 1024)))  # 1MB
    ENABLE_BOT_PROTECTION: bool = os.getenv("ENABLE_BOT_PROTECTION", "True").lower() == "true"

    # Configurações de performance
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutos

    # Configurações de Cache Inteligente
    MAX_CACHE_MEMORY_MB: int = int(os.getenv("MAX_CACHE_MEMORY_MB", "100"))  # Limite de 100MB para cache
    CACHE_CLEANUP_INTERVAL: int = int(os.getenv("CACHE_CLEANUP_INTERVAL", "1800"))  # Limpeza a cada 30min

    # HTTP Connection Pool
    HTTP_POOL_CONNECTIONS: int = int(os.getenv("HTTP_POOL_CONNECTIONS", "10"))
    HTTP_POOL_MAXSIZE: int = int(os.getenv("HTTP_POOL_MAXSIZE", "10"))
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))

    # Warm-up Configuration
    ENABLE_WARMUP: bool = os.getenv("ENABLE_WARMUP", "True").lower() == "true"
    WARMUP_QUERIES: list = os.getenv("WARMUP_QUERIES", "velocidade,alcool,celular").split(",")

    # Configurações de SSL/TLS para produção
    SSL_KEYFILE: str = os.getenv("SSL_KEYFILE")
    SSL_CERTFILE: str = os.getenv("SSL_CERTFILE")

    # Workers para produção
    WORKERS: int = int(os.getenv("WORKERS", "1"))
    
    def __init__(self):
        # Verificar se SECRET_KEY está definida
        if not self.SECRET_KEY:
            if self.DEBUG:
                # Em ambiente de desenvolvimento, gerar uma chave segura
                self.SECRET_KEY = secrets.token_urlsafe(32)
                import warnings
                warnings.warn(
                    "AVISO: Usando uma SECRET_KEY gerada automaticamente para desenvolvimento. "
                    "Defina SECRET_KEY nas variáveis de ambiente para um ambiente seguro.",
                    UserWarning
                )
            else:
                # Em ambiente de produção, exigir uma SECRET_KEY
                print("ERRO CRÍTICO: SECRET_KEY não está definida nas variáveis de ambiente!")
                print("Por motivos de segurança, a aplicação não pode iniciar sem uma SECRET_KEY em ambiente de produção.")
                print("Gere uma chave segura com: python -c 'import secrets; print(secrets.token_urlsafe(32))'")
                sys.exit(1)

        # Validar configurações de produção
        if not self.DEBUG:
            self._validate_production_config()

    def _validate_production_config(self):
        """Valida configurações específicas para produção."""
        # Verificar se CORS não está muito permissivo em produção
        if "*" in self.CORS_ORIGINS and not self.DEBUG:
            import warnings
            warnings.warn(
                "AVISO: CORS configurado com '*' em produção. "
                "Configure CORS_ORIGINS com domínios específicos.",
                UserWarning
            )

        # Verificar SSL em produção
        if not self.SSL_CERTFILE and not self.DEBUG:
            import warnings
            warnings.warn(
                "AVISO: SSL não configurado em produção. "
                "Configure SSL_CERTFILE e SSL_KEYFILE para HTTPS.",
                UserWarning
            )

    @property
    def is_production(self) -> bool:
        """Verifica se está em ambiente de produção."""
        return not self.DEBUG

    def get_cors_origins(self) -> List[str]:
        """Retorna origins do CORS de forma segura."""
        if self.DEBUG:
            return self.CORS_ORIGINS + [
                "http://localhost:8080",
                "http://localhost:8081",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8081"
            ]
        return [origin for origin in self.CORS_ORIGINS if origin != "*"]

settings = Settings()