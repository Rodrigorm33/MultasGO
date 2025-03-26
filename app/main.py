import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
from sqlalchemy import text

from app.api.api import api_router
from app.core.config import settings
from app.core.logger import logger
from app.db.database import get_db

# Determinar o caminho correto para as pastas static e templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Definir o lifespan da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código de inicialização - executado antes da aplicação receber requisições
    logger.info("Iniciando a API MultasGO...")
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        logger.info("Conexão com o banco de dados verificada com sucesso.")
    except Exception as e:
        logger.error(f"Erro na conexão: {str(e)}")
    
    yield  # A aplicação executa aqui
    
    # Código de encerramento - executado quando a aplicação está sendo desligada
    logger.info("Encerrando a API MultasGO...")

# Inicializar aplicação FastAPI com o novo parâmetro lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configuração para servir arquivos estáticos com caminho correto
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Configuração para templates HTML com caminho correto
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Configurar CORS para o frontend
origins = [
    "http://localhost:8080",
    "http://localhost:3000",
    "https://multasgo.up.railway.app",  # Altere conforme necessário quando tiver o domínio do Railway
    *settings.ALLOWED_HOSTS
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas da API
app.include_router(api_router, prefix="/api/v1")

# Rota para servir a página principal HTML
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Endpoint para a página principal da aplicação.
    
    Retorna a interface web da aplicação MultasGO.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/explorador", response_class=HTMLResponse)
async def explorador_page(request: Request):
    """
    Endpoint para a página do explorador de infrações.
    
    Retorna a interface web para explorar as infrações com filtros avançados.
    """
    return templates.TemplateResponse("explorador.html", {"request": request})

@app.get("/noticias", response_class=HTMLResponse)
async def noticias_page(request: Request):
    """
    Endpoint para a página de notícias.
    
    Retorna a interface web com as notícias do MultasGO.
    """
    return templates.TemplateResponse("noticias.html", {"request": request})

# Rota API para informações básicas (acesso via JSON)
@app.get("/api", 
    tags=["recursos-api"],
    summary="Raiz da API MultasGO",
    description="Ponto de entrada principal da API MultasGO com links para recursos importantes.",
    response_description="Informações básicas da API e links para recursos")
def api_root():
    """
    Endpoint raiz da API.
    
    Fornece informações básicas sobre a API MultasGO e links para outros recursos,
    incluindo documentação e base da API v1.
    """
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "descricao": "API para pesquisa de autos de infração de trânsito",
        "api_docs": "/docs",
        "api_v1": "/api/v1",
        "health": "/health"
    }

@app.get("/health", 
    tags=["recursos-api"],
    summary="Verificação de saúde do sistema",
    description="Verifica o estado de saúde da API, incluindo conectividade com o banco de dados.",
    responses={
        200: {"description": "Sistema operacional com banco de dados conectado"},
        503: {"description": "Sistema com problemas de conectividade ao banco de dados"}
    })
def health_check():
    """
    Verifica a saúde do sistema.
    
    Este endpoint fornece informações sobre:
    - Estado geral do sistema
    - Conectividade com o banco de dados
    - Versão atual da aplicação
    - Timestamp da verificação
    
    É útil para monitoramento e diagnóstico do serviço.
    """
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "conectado",
            "version": settings.PROJECT_VERSION,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {e}")
        return JSONResponse(
            content={
                "status": "erro",
                "database": "desconectado",
                "error": str(e),
                "version": settings.PROJECT_VERSION,
                "timestamp": datetime.now().isoformat()
            }, 
            status_code=503
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG
    )