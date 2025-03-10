import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from typing import Any, Dict
import time
from datetime import datetime

from app.api.api import api_router
from app.core.config import settings
from app.core.logger import logger
from app.db.database import get_db, engine
from app.routers import infracoes

# Inicializar a aplicação FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS
origins = settings.ALLOWED_HOSTS if hasattr(settings, "ALLOWED_HOSTS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar templates e arquivos estáticos
templates_dir = "app/templates"
static_dir = "app/static"

# Verificar se os diretórios existem
if os.path.exists(templates_dir):
    templates = Jinja2Templates(directory=templates_dir)
else:
    logger.warning(f"Diretório de templates não encontrado: {templates_dir}")
    templates = None

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    logger.warning(f"Diretório de arquivos estáticos não encontrado: {static_dir}")

# Classe personalizada para lidar com codificação UTF-8
class UJSONResponse(JSONResponse):
    media_type = "application/json"
    
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            separators=(",", ":"),
        ).encode("utf-8")

# Sobrescrever o manipulador de respostas padrão
app.router.default_response_class = UJSONResponse

# Configurar cabeçalhos CORS para UTF-8
@app.middleware("http")
async def add_charset_middleware(request: Request, call_next):
    response = await call_next(request)
    if response.headers.get("content-type") == "application/json":
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response

# Incluir as rotas da API
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """
    Evento executado na inicialização da aplicação.
    """
    logger.info("Iniciando a aplicação MultasGO...")
    
    try:
        # Testar conexão com o banco de dados
        db = next(get_db())
        db.execute(text("SELECT 1"))
        logger.info("Conexão com o banco de dados verificada com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        logger.warning("A aplicação continuará mesmo com erro na conexão com o banco de dados.")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Página inicial do MultasGO.
    """
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(content="<html><body><h1>MultasGO API</h1><p>Acesse /docs para a documentação da API.</p></body></html>")

@app.get("/sobre", response_class=HTMLResponse)
async def sobre(request: Request):
    """
    Página Sobre do MultasGO.
    """
    if templates:
        return templates.TemplateResponse("sobre.html", {"request": request})
    return HTMLResponse(content="<html><body><h1>Sobre o MultasGO</h1><p>API para pesquisa de autos de infração de trânsito.</p></body></html>")

@app.get("/contato", response_class=HTMLResponse)
async def contato(request: Request):
    """
    Página de Contato do MultasGO.
    """
    if templates:
        return templates.TemplateResponse("contato.html", {"request": request})
    return HTMLResponse(content="<html><body><h1>Contato MultasGO</h1><p>Página de contato.</p></body></html>")

@app.get("/suporte", response_class=HTMLResponse)
async def suporte(request: Request):
    """
    Página de Suporte do MultasGO (mesmo conteúdo da página de Contato).
    """
    if templates:
        return templates.TemplateResponse("suporte.html", {"request": request})
    return HTMLResponse(content="<html><body><h1>Suporte MultasGO</h1><p>Página de suporte.</p></body></html>")

@app.get("/api")
def api_root():
    return {"message": "Bem-vindo à API MultasGO. Acesse /docs para a documentação."}

@app.get("/health")
def health_check():
    """
    Endpoint para verificação de saúde da aplicação.
    """
    start_time = time.time()
    
    try:
        # Verificar a conexão com o banco de dados
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "conectado"
        db_error = None
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {e}")
        db_status = "erro"
        db_error = str(e)
    
    end_time = time.time()
    response_time = round((end_time - start_time) * 1000, 2)  # em milissegundos
    
    health_info = {
        "status": "ok" if db_status == "conectado" else "erro",
        "database": db_status,
        "version": settings.PROJECT_VERSION,
        "timestamp": datetime.now().isoformat(),
        "response_time_ms": response_time
    }
    
    if db_error:
        health_info["database_error"] = db_error
        # Retornar status 503 Service Unavailable se o banco de dados não estiver disponível
        return JSONResponse(content=health_info, status_code=503)
    
    return health_info

if __name__ == "__main__":
    import uvicorn
    
    # Obter a porta da variável de ambiente ou usar 8000 como padrão
    port = int(os.environ.get("PORT", 8000))
    
    # Iniciar o servidor
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG
    )