import logging
import sys
from .config import settings

# Configuração do logger
def setup_logger():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configuração básica do logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log", mode="a")
        ]
    )
    
    # Criação do logger da aplicação
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(log_level)
    
    # Reduzir o nível de log de bibliotecas externas
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # Crie um handler para escrever os logs em um arquivo
    file_handler = logging.FileHandler("app.log")
    file_handler.setLevel(logging.INFO)

    # Crie um handler para escrever os logs no console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Crie um formatter e adicione-o aos handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Adicione os handlers ao logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Instância do logger para uso em toda a aplicação
logger = setup_logger()