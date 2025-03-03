import os
from dotenv import load_dotenv
from pathlib import Path

# Carrega as variáveis de ambiente do arquivo .env apenas se ele existir
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print("Arquivo .env encontrado e carregado.")
else:
    print("Arquivo .env não encontrado. Usando variáveis de ambiente do sistema.")

# Função para obter variável de ambiente com fallback e log
def get_env_variable(var_name, default_value=None, is_secret=False):
    value = os.getenv(var_name, default_value)
    if value is None:
        print(f"AVISO: Variável de ambiente {var_name} não encontrada!")
    elif is_secret:
        masked_value = value[:5] + "..." if len(value) > 8 else "***"
        print(f"INFO: {var_name} configurado como {masked_value}")
    else:
        print(f"INFO: {var_name} configurado como {value}")
    return value

# Verifica se estamos no ambiente Railway
is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None

class Settings:
    # Informações da aplicação
    APP_NAME: str = get_env_variable("APP_NAME", "MultasGO")
    PROJECT_NAME: str = get_env_variable("PROJECT_NAME", "MultasGO")
    PROJECT_DESCRIPTION: str = get_env_variable("PROJECT_DESCRIPTION", "API para pesquisa de autos de infração de trânsito")
    PROJECT_VERSION: str = get_env_variable("PROJECT_VERSION", "1.0.0")
    DEBUG: bool = get_env_variable("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = get_env_variable("LOG_LEVEL", "INFO")
    
    # Configurações do banco de dados
    # Se estiver no Railway, use o endereço do PostgreSQL fornecido
    DATABASE_URL: str = None
    if is_railway:
        # Tentar obter a URL do banco de dados de várias fontes possíveis
        db_url = None
        
        # Opção 1: Variável DATABASE_URL direta
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            print("Usando DATABASE_URL direta")
        
        # Opção 2: Variável compartilhada do PostgreSQL
        if not db_url:
            pg_user = os.getenv("PGUSER") or os.getenv("POSTGRES_USER") or "postgres"
            pg_password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
            pg_host = os.getenv("PGHOST") or "postgres.railway.internal"
            pg_port = os.getenv("PGPORT") or "5432"
            pg_db = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB") or "railway"
            
            # Verificar se temos pelo menos o usuário e a senha
            if pg_password:
                db_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
                print(f"Construindo DATABASE_URL a partir de variáveis PG_*: postgresql://{pg_user}:***@{pg_host}:{pg_port}/{pg_db}")
        
        # Opção 3: Usar valores fixos como último recurso
        if not db_url:
            print("AVISO: Nenhuma variável de banco de dados encontrada! Usando valores fixos para o Railway.")
            db_url = "postgresql://postgres:FbFuyWYNXEEGPwdBUsvrUvhrtqaKGSOs@postgres.railway.internal:5432/railway"
        
        # Verificar se a URL não está vazia antes de adicionar parâmetros
        if db_url and db_url.startswith("postgresql://"):
            # Adicionar parâmetros de conexão para melhorar a estabilidade
            if "?" not in db_url:
                db_url += "?"
            else:
                db_url += "&"
                
            # Adicionar parâmetros para retry e timeout
            db_url += "connect_timeout=10&application_name=multasgo&keepalives=1&keepalives_idle=5&keepalives_interval=2&keepalives_count=3"
            
            DATABASE_URL = db_url
            
            # Exibir URL de forma segura (sem senha)
            try:
                print(f"URL final do banco de dados: (formato seguro)")
            except Exception as e:
                print(f"Erro ao exibir URL do banco de dados: {e}")
        else:
            print("ERRO: URL do banco de dados inválida ou vazia!")
            # Usar uma URL padrão para evitar erros
            DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/railway"
    else:
        # Usa o DATABASE_URL do ambiente ou o valor padrão
        DATABASE_URL = get_env_variable("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/multas_db", is_secret=True)
    
    # Configurações de segurança
    SECRET_KEY: str = get_env_variable("SECRET_KEY", "chave_secreta_padrao_nao_use_em_producao", is_secret=True)
    ALLOWED_HOSTS: list = get_env_variable("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    
    # Configurações de busca fuzzy
    FUZZY_SEARCH_THRESHOLD: int = int(get_env_variable("FUZZY_SEARCH_THRESHOLD", "70"))
    MAX_SEARCH_RESULTS: int = int(get_env_variable("MAX_SEARCH_RESULTS", "20"))

settings = Settings()