import os
import sys
from fastapi import FastAPI
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultasGO")

# Adicionar logs de diagnóstico
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Environment variables: {list(os.environ.keys())}")
logger.info(f"PORT environment variable: {os.environ.get('PORT', 'não definido')}")

# Inicializar a aplicação FastAPI
app = FastAPI(
    title="MultasGO",
    description="API para pesquisa de autos de infração de trânsito",
    version="1.0.0",
)

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