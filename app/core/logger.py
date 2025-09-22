"""
Sistema de logging otimizado para produção com rotação e filtragem inteligente.
"""
import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import settings

class SecurityFilter(logging.Filter):
    """Filtro para logs de segurança."""

    def filter(self, record):
        # Não logar informações sensíveis
        sensitive_patterns = ['password', 'token', 'secret', 'key', 'authorization']
        message = str(record.getMessage()).lower()

        for pattern in sensitive_patterns:
            if pattern in message:
                record.msg = f"[SENSITIVE DATA FILTERED] {record.msg[:50]}..."
                break

        return True

class StructuredFormatter(logging.Formatter):
    """Formatter para logs estruturados em JSON."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Adicionar informações extras se existirem
        if hasattr(record, 'user_ip'):
            log_entry['user_ip'] = record.user_ip
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time

        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging():
    """Configura o sistema de logging otimizado."""

    # Criar diretório de logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configurar nível baseado em ambiente
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configurar logger principal
    logger = logging.getLogger('MultasGO')
    logger.setLevel(log_level)

    # Limpar handlers existentes
    logger.handlers.clear()

    # Handler para arquivo principal (com rotação)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "multasgo.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )

    # Handler para logs de segurança
    security_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "security.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=10,
        encoding='utf-8'
    )

    # Handler para console (apenas em desenvolvimento)
    console_handler = logging.StreamHandler(sys.stdout)

    # Configurar formatters
    if settings.DEBUG:
        # Formato simples para desenvolvimento
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(simple_formatter)
        console_handler.setFormatter(simple_formatter)
    else:
        # Formato estruturado para produção
        structured_formatter = StructuredFormatter()
        file_handler.setFormatter(structured_formatter)

        # Console em produção com menos detalhes
        production_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(production_formatter)

    # Configurar filtros
    security_filter = SecurityFilter()
    file_handler.addFilter(security_filter)
    console_handler.addFilter(security_filter)

    # Configurar níveis por handler
    file_handler.setLevel(log_level)
    security_handler.setLevel(logging.WARNING)

    if settings.DEBUG:
        console_handler.setLevel(logging.INFO)
    else:
        console_handler.setLevel(logging.WARNING)

    # Adicionar handlers
    logger.addHandler(file_handler)
    logger.addHandler(security_handler)

    if settings.DEBUG or not settings.is_production:
        logger.addHandler(console_handler)

    # Configurar loggers de terceiros
    configure_third_party_loggers()

    return logger

def configure_third_party_loggers():
    """Configura loggers de bibliotecas terceiras."""

    # SQLAlchemy - reduzir verbosidade
    sql_loggers = [
        'sqlalchemy.engine',
        'sqlalchemy.pool',
        'sqlalchemy.dialects',
        'sqlalchemy.orm'
    ]

    for logger_name in sql_loggers:
        logger = logging.getLogger(logger_name)
        if settings.DEBUG:
            logger.setLevel(logging.WARNING)
        else:
            logger.setLevel(logging.ERROR)

    # Uvicorn - controlar logs de acesso
    uvicorn_loggers = [
        'uvicorn.access',
        'uvicorn.error',
        'uvicorn'
    ]

    for logger_name in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        if settings.DEBUG:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

    # FastAPI
    fastapi_logger = logging.getLogger('fastapi')
    fastapi_logger.setLevel(logging.WARNING)

    # Outros loggers verbose
    noisy_loggers = [
        'urllib3.connectionpool',
        'requests.packages.urllib3',
        'charset_normalizer'
    ]

    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)

def get_request_logger(request_id: str = None, user_ip: str = None):
    """Cria logger com contexto de requisição."""
    logger = logging.getLogger('MultasGO.request')

    # Adapter para adicionar contexto
    class RequestAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            if self.extra.get('request_id'):
                msg = f"[{self.extra['request_id']}] {msg}"
            if self.extra.get('user_ip'):
                msg = f"[{self.extra['user_ip']}] {msg}"
            return msg, kwargs

    extra = {}
    if request_id:
        extra['request_id'] = request_id
    if user_ip:
        extra['user_ip'] = user_ip

    return RequestAdapter(logger, extra)

def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "WARNING"):
    """Log específico para eventos de segurança."""
    security_logger = logging.getLogger('MultasGO.security')

    log_data = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        'details': details,
        'severity': severity
    }

    level = getattr(logging, severity.upper(), logging.WARNING)
    security_logger.log(level, f"Security Event: {event_type}", extra=log_data)

def log_performance(operation: str, execution_time: float, details: Dict[str, Any] = None):
    """Log para métricas de performance."""
    perf_logger = logging.getLogger('MultasGO.performance')

    log_data = {
        'operation': operation,
        'execution_time': execution_time,
        'timestamp': datetime.utcnow().isoformat()
    }

    if details:
        log_data.update(details)

    if execution_time > 5.0:  # Log slow operations
        perf_logger.warning(f"Slow operation: {operation} took {execution_time:.2f}s", extra=log_data)
    elif execution_time > 1.0:
        perf_logger.info(f"Operation: {operation} took {execution_time:.2f}s", extra=log_data)

def log_api_access(method: str, path: str, status_code: int, response_time: float,
                  user_ip: str = None, user_agent: str = None):
    """Log específico para acesso à API."""
    access_logger = logging.getLogger('MultasGO.access')

    log_data = {
        'method': method,
        'path': path,
        'status_code': status_code,
        'response_time': response_time,
        'timestamp': datetime.utcnow().isoformat(),
        'user_ip': user_ip,
        'user_agent': user_agent
    }

    if status_code >= 500:
        level = logging.ERROR
    elif status_code >= 400:
        level = logging.WARNING
    else:
        level = logging.INFO

    access_logger.log(level, f"{method} {path} - {status_code} ({response_time:.2f}s)", extra=log_data)

# Funções de conveniência (mantém compatibilidade)
def log_info(message: str, extra_data: dict = None):
    """Log estruturado para informações importantes."""
    logger = logging.getLogger('MultasGO')
    if extra_data:
        logger.info(f"{message}", extra=extra_data)
    else:
        logger.info(message)

def log_error(message: str, error: Exception = None):
    """Log estruturado para erros."""
    logger = logging.getLogger('MultasGO')
    if error:
        logger.error(f"{message} - {type(error).__name__}: {str(error)}",
                    extra={'error_type': type(error).__name__, 'error_message': str(error)})
    else:
        logger.error(message)

def log_warning(message: str, extra_data: dict = None):
    """Log estruturado para avisos."""
    logger = logging.getLogger('MultasGO')
    if extra_data:
        logger.warning(f"{message}", extra=extra_data)
    else:
        logger.warning(message)

def cleanup_old_logs(days_to_keep: int = 30):
    """Remove logs antigos para economizar espaço."""
    log_dir = Path("logs")
    if not log_dir.exists():
        return

    import time
    cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)

    for log_file in log_dir.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                logger.info(f"Removed old log file: {log_file}")
            except Exception as e:
                logger.error(f"Failed to remove old log file {log_file}: {e}")

# Configurar logging na importação
logger = setup_logging()

# Export do logger principal para compatibilidade
__all__ = ['logger', 'log_info', 'log_error', 'log_warning', 'log_security_event',
          'log_performance', 'log_api_access', 'get_request_logger', 'cleanup_old_logs']