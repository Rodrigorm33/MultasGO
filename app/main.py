import os
import sys
import socket
import platform
from fastapi import FastAPI, Request
import logging
import traceback

# Configurar logging com mais detalhes
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MultasGO")

# Adicionar logs de diagnóstico detalhados
logger.info("=" * 50)
logger.info("INICIANDO APLICAÇÃO MULTASGO")
logger.info("=" * 50)
logger.info(f"Python version: {sys.version}")
logger.info(f"Platform info: {platform.platform()}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Environment variables: {list(os.environ.keys())}")
logger.info(f"PORT environment variable: {os.environ.get('PORT', 'não definido')}")
logger.info(f"RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT', 'não definido')}")

# Tentar obter informações de rede
try:
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    logger.info(f"Hostname: {hostname}")
    logger.info(f"IP Address: {ip_address}")
except Exception as e:
    logger.error(f"Erro ao obter informações de rede: {e}")

# Inicializar a aplicação FastAPI
app = FastAPI(
    title="MultasGO",
    description="API para pesquisa de autos de infração de trânsito",
    version="1.0.0",
)

# Middleware para logging de todas as requisições
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Requisição recebida: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Resposta enviada: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Erro ao processar requisição: {e}")
        logger.error(traceback.format_exc())
        raise

# Endpoint simples para diagnóstico
@app.get("/ping")
def ping():
    """
    Endpoint simples para verificar se a aplicação está funcionando.
    """
    logger.info("Endpoint /ping acessado")
    try:
        # Coletar informações de diagnóstico
        diagnostico = {
            "ping": "pong",
            "status": "ok",
            "port": os.environ.get("PORT", "não definido"),
            "python_version": sys.version,
            "cwd": os.getcwd(),
            "env_vars": list(os.environ.keys()),
            "railway_env": os.environ.get("RAILWAY_ENVIRONMENT", "não definido"),
            "railway_service": os.environ.get("RAILWAY_SERVICE_NAME", "não definido"),
            "railway_project": os.environ.get("RAILWAY_PROJECT_NAME", "não definido"),
            "railway_domain": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "não definido")
        }
        logger.info(f"Diagnóstico: {diagnostico}")
        return diagnostico
    except Exception as e:
        logger.error(f"Erro no endpoint /ping: {e}")
        logger.error(traceback.format_exc())
        return {"ping": "error", "error": str(e)}

# Endpoint raiz simplificado para diagnóstico
@app.get("/")
def root():
    """
    Endpoint raiz simplificado para diagnóstico.
    """
    logger.info("Endpoint raiz (/) acessado")
    return {
        "message": "API MultasGO funcionando",
        "status": "ok",
        "endpoints": [
            "/ping",
            "/docs",
            "/redoc"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    # Obter a porta da variável de ambiente PORT ou usar 8080 como padrão
    port = int(os.environ.get("PORT", 8080))
    
    # Iniciar o servidor
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="debug"
    )