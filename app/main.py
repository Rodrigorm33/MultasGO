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

# Adicionar logs de diagnóstico
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Environment variables: {list(os.environ.keys())}")
logger.info(f"PORT environment variable: {os.environ.get('PORT', 'não definido')}")

# Recriar as tabelas no banco de dados (drop e create)
try:
    logger.info("Recriando as tabelas no banco de dados...")
    logger.info(f"Usando DATABASE_URL: {settings.DATABASE_URL[:20]}...")  # Mostra apenas o início da URL por segurança
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("Tabelas recriadas com sucesso.")
    
    # Verificar se as tabelas foram realmente criadas
    tabelas = check_tables()
    if tabelas:
        logger.info(f"Tabelas verificadas após criação: {tabelas}")
    else:
        logger.warning("Nenhuma tabela encontrada após tentativa de criação!")
except Exception as e:
    logger.error(f"Erro ao recriar tabelas: {e}")
    logger.error("A aplicação continuará, mas pode não funcionar corretamente.")

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
# Comentado temporariamente para diagnóstico
# templates = Jinja2Templates(directory="app/templates")
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
    logger.info(f"Recebida requisição: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        if response.headers.get("content-type") == "application/json":
            response.headers["content-type"] = "application/json; charset=utf-8"
        logger.info(f"Resposta enviada: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Erro ao processar requisição: {e}")
        raise

# Endpoint simples para diagnóstico
@app.get("/ping")
def ping():
    """
    Endpoint simples para verificar se a aplicação está funcionando.
    Não depende do banco de dados ou de outras dependências.
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
            "/api",
            "/health",
            "/check-tables",
            "/docs",
            "/redoc"
        ]
    }

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
        logger.info(f"Procurando arquivo CSV em: {csv_path}")
        
        # Verificar se o arquivo CSV existe
        if not os.path.exists(csv_path):
            logger.warning(f"Arquivo CSV não encontrado: {csv_path}. A aplicação continuará sem importar dados.")
            
            # Listar arquivos no diretório atual para debug
            try:
                arquivos = os.listdir(os.getcwd())
                logger.info(f"Arquivos encontrados no diretório atual: {arquivos}")
            except Exception as e:
                logger.error(f"Erro ao listar arquivos: {e}")
            
            return
        
        # Importar os dados do CSV para o banco de dados
        try:
            logger.info("Iniciando importação de dados...")
            registros_importados = importar_csv_para_db(db, csv_path, force_update=False)
            
            if registros_importados > 0:
                logger.info(f"Dados importados com sucesso: {registros_importados} registros")
            else:
                logger.info("Nenhum dado foi importado")
                
            # Verificar novamente as tabelas após a importação
            tabelas = check_tables()
            if tabelas:
                logger.info(f"Tabelas após importação: {tabelas}")
            else:
                logger.warning("Nenhuma tabela encontrada após importação!")
        except Exception as e:
            logger.error(f"Erro durante a importação do CSV: {e}")
            logger.info("A aplicação continuará sem importar dados.")
    
    except Exception as e:
        logger.error(f"Erro durante a inicialização da aplicação: {e}")
        logger.info("A aplicação continuará mesmo com erro na inicialização.")

# Comentado temporariamente para diagnóstico
# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request):
#     """
#     Página inicial do MultasGO.
#     """
#     return templates.TemplateResponse("index.html", {"request": request})

# @app.get("/sobre", response_class=HTMLResponse)
# async def sobre(request: Request):
#     """
#     Página Sobre do MultasGO.
#     """
#     return templates.TemplateResponse("sobre.html", {"request": request})

# @app.get("/contato", response_class=HTMLResponse)
# async def contato(request: Request):
#     """
#     Página de Contato do MultasGO.
#     """
#     return templates.TemplateResponse("contato.html", {"request": request})

# @app.get("/suporte", response_class=HTMLResponse)
# async def suporte(request: Request):
#     """
#     Página de Suporte do MultasGO (mesmo conteúdo da página de Contato).
#     """
#     return templates.TemplateResponse("suporte.html", {"request": request})

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

@app.get("/check-tables")
def check_tables_endpoint():
    """
    Endpoint temporário para verificar as tabelas no banco de dados.
    """
    tables = check_tables()
    if tables:
        return {"message": "Tabelas encontradas no banco de dados", "tables": tables}
    else:
        return {"message": "Nenhuma tabela encontrada no banco de dados"}

if __name__ == "__main__":
    import uvicorn
    
    # Obter a porta da variável de ambiente PORT ou usar 8000 como padrão
    port = int(os.environ.get("PORT", 8080))
    
    # Iniciar o servidor
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG
    )