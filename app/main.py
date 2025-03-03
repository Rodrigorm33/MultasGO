import os
import sys
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
from app.scripts.check_tables import check_tables

# Verificar se o engine está disponível antes de tentar recriar as tabelas
if engine is not None:
    try:
        # Comentando a recriação das tabelas para evitar problemas
        # logger.info("Recriando as tabelas no banco de dados...")
        # Base.metadata.drop_all(bind=engine)
        # Base.metadata.create_all(bind=engine)
        # logger.info("Tabelas recriadas com sucesso.")
        
        # Apenas criar as tabelas se não existirem
        logger.info("Verificando e criando tabelas se necessário...")
        Base.metadata.create_all(bind=engine)
        logger.info("Verificação de tabelas concluída.")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")
        logger.info("A aplicação continuará mesmo com erro na criação de tabelas.")
else:
    logger.warning("Engine do banco de dados não disponível. Tabelas não serão criadas.")

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
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Environment variables: {[k for k in os.environ.keys()]}")
    
    try:
        # Verificar se o arquivo CSV existe
        csv_path = os.path.join(os.getcwd(), "dbautos.csv")
        if os.path.exists(csv_path):
            logger.info(f"Arquivo CSV encontrado: {csv_path}")
        else:
            logger.warning(f"Arquivo CSV não encontrado: {csv_path}")
        
        # Tentar obter uma sessão do banco de dados, mas não falhar se não conseguir
        try:
            db = next(get_db())
            logger.info("Conexão com o banco de dados estabelecida com sucesso")
            
            # Importar os dados do CSV para o banco de dados
            if os.path.exists(csv_path):
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
            logger.error(f"Erro ao conectar ao banco de dados: {e}")
            logger.info("A aplicação continuará mesmo sem conexão com o banco de dados.")
    
    except Exception as e:
        logger.error(f"Erro durante a inicialização da aplicação: {e}")
        logger.info("A aplicação continuará mesmo com erro na inicialização.")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Página inicial do MultasGO.
    """
    logger.info("Endpoint raiz acessado.")
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

@app.get("/ping")
def ping():
    """
    Endpoint simples para verificar se a aplicação está respondendo.
    Não depende do banco de dados.
    """
    return {"status": "ok", "message": "pong"}

@app.get("/diagnostico")
def diagnostico():
    """
    Endpoint de diagnóstico que retorna informações sobre o ambiente.
    Não depende do banco de dados.
    """
    env_vars = {k: v for k, v in os.environ.items() 
                if not ('SECRET' in k or 'PASSWORD' in k or 'KEY' in k)}
    
    # Verificar se o arquivo CSV existe
    csv_path = os.path.join(os.getcwd(), "dbautos.csv")
    csv_exists = os.path.exists(csv_path)
    
    # Verificar se os diretórios de templates e estáticos existem
    templates_dir = "app/templates"
    static_dir = "app/static"
    
    return {
        "status": "ok",
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "environment": {
            "railway_environment": os.environ.get("RAILWAY_ENVIRONMENT"),
            "debug": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
            "port": os.environ.get("PORT"),
        },
        "files": {
            "csv_exists": csv_exists,
            "templates_dir_exists": os.path.exists(templates_dir),
            "static_dir_exists": os.path.exists(static_dir),
        },
        "database_url_format": "postgresql://[username]:[password]@[host]:[port]/[database]",
        "environment_variables": list(env_vars.keys()),
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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
        return {
            "status": "warning",
            "database": "desconectado",
            "error": str(e)
        }

@app.get("/check-tables")
def check_tables_endpoint():
    """
    Endpoint temporário para verificar as tabelas no banco de dados.
    """
    try:
        tables = check_tables()
        if tables:
            return {"message": "Tabelas encontradas no banco de dados", "tables": tables}
        else:
            return {"message": "Nenhuma tabela encontrada no banco de dados"}
    except Exception as e:
        logger.error(f"Erro ao verificar tabelas: {e}")
        return {"message": "Erro ao verificar tabelas", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    # Iniciar o servidor
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )