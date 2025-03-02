import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
import json
from typing import Any, Dict

from app.api.api import api_router
from app.core.config import settings
from app.core.logger import logger
from app.db.database import get_db, engine, Base
from app.services.import_service import importar_csv_para_db
from app.routers import infracoes

# Recriar as tabelas no banco de dados (drop e create)
logger.info("Recriando as tabelas no banco de dados...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
logger.info("Tabelas recriadas com sucesso.")

# Inicializar a aplicação FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar as origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar templates e arquivos estáticos
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
    Importa os dados do CSV para o banco de dados.
    """
    logger.info("Iniciando a aplicação...")
    
    try:
        # Obter uma sessão do banco de dados
        db = next(get_db())
        
        # Caminho para o arquivo CSV
        csv_path = os.path.join(os.getcwd(), "dbautos.csv")
        
        # Verificar se o arquivo CSV existe
        if not os.path.exists(csv_path):
            logger.warning(f"Arquivo CSV não encontrado: {csv_path}. A aplicação continuará sem importar dados.")
            return
        
        # Importar os dados do CSV para o banco de dados
        try:
            registros_importados = importar_csv_para_db(db, csv_path, force_update=False)
            
            if registros_importados > 0:
                logger.info(f"Dados importados com sucesso: {registros_importados} registros")
            else:
                logger.info("Nenhum dado foi importado")
        except Exception as e:
            logger.error(f"Erro durante a importação do CSV: {e}")
            logger.info("A aplicação continuará sem importar dados.")
    
    except Exception as e:
        logger.error(f"Erro durante a inicialização da aplicação: {e}")
        logger.info("A aplicação continuará mesmo com erro na inicialização.")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Página inicial do MultasGO.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/sobre", response_class=HTMLResponse)
async def sobre(request: Request):
    """
    Página Sobre do MultasGO.
    """
    return templates.TemplateResponse("sobre.html", {"request": request})

@app.get("/contato", response_class=HTMLResponse)
async def contato(request: Request):
    """
    Página de Contato do MultasGO.
    """
    return templates.TemplateResponse("contato.html", {"request": request})

@app.get("/suporte", response_class=HTMLResponse)
async def suporte(request: Request):
    """
    Página de Suporte do MultasGO (mesmo conteúdo da página de Contato).
    """
    return templates.TemplateResponse("suporte.html", {"request": request})

@app.get("/api")
def api_root():
    return {"message": "Bem-vindo à API MultasGO. Acesse /docs para a documentação."}

@app.get("/health")
def health_check():
    """
    Endpoint para verificação de saúde da aplicação.
    """
    try:
        # Verificar a conexão com o banco de dados
        db = next(get_db())
        db.execute("SELECT 1")
        
        return {
            "status": "ok",
            "database": "conectado"
        }
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na verificação de saúde: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Iniciar o servidor
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )