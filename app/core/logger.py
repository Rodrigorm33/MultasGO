import logging
import sys
import os
from .config import settings

# Configuração do logger
def setup_logger():
    # Determinar o nível de log com base na configuração
    log_level = logging.DEBUG if settings.DEBUG else getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Criar diretório de logs se não existir
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Nome do arquivo de log com data
    from datetime import datetime
    log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    
    # Formato detalhado para o log
    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    
    # Configuração básica do logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode="a", encoding="utf-8")
        ]
    )
    
    # Criação do logger da aplicação
    app_logger = logging.getLogger(settings.APP_NAME)
    app_logger.setLevel(log_level)
    
    # Configurar níveis de log para bibliotecas externas
    if settings.DEBUG:
        # Em modo de debug, mostrar mais logs das bibliotecas
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)  # Mostrar queries SQL
    else:
        # Em produção, reduzir o nível de log de bibliotecas externas
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    app_logger.debug(f"Logger configurado com nível: {logging.getLevelName(log_level)}")
    return app_logger

# Instância do logger para uso em toda a aplicação
logger = setup_logger()