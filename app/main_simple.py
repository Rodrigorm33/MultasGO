"""
Versão simplificada da aplicação MultasGO para diagnóstico.
Esta versão não depende do banco de dados e serve apenas para verificar
se o ambiente está configurado corretamente.
"""
import os
import sys
from fastapi import FastAPI
import uvicorn

# Criar a aplicação FastAPI
app = FastAPI(
    title="MultasGO Diagnóstico",
    description="Versão simplificada para diagnóstico",
    version="1.0.0",
)

@app.get("/")
def read_root():
    """Endpoint raiz."""
    return {"message": "Bem-vindo à versão de diagnóstico do MultasGO"}

@app.get("/ping")
def ping():
    """Endpoint de ping para verificar se a aplicação está respondendo."""
    return {"status": "ok", "message": "pong"}

@app.get("/info")
def info():
    """Endpoint para obter informações sobre o ambiente."""
    return {
        "python_version": sys.version,
        "environment": {
            "railway_environment": os.environ.get("RAILWAY_ENVIRONMENT"),
            "port": os.environ.get("PORT"),
        },
        "environment_variables": [k for k in os.environ.keys() 
                                if not ('SECRET' in k or 'PASSWORD' in k or 'KEY' in k)],
        "current_directory": os.getcwd(),
        "directory_contents": os.listdir(),
    }

if __name__ == "__main__":
    # Obter a porta do ambiente ou usar 8000 como padrão
    port = int(os.environ.get("PORT", 8000))
    
    # Iniciar o servidor
    uvicorn.run(
        "app.main_simple:app",
        host="0.0.0.0",
        port=port,
        log_level="debug"
    ) 