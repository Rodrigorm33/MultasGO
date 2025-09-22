import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from datetime import datetime
from sqlalchemy import text

from app.api.api import api_router
from app.core.config import settings
from app.core.logger import logger
from app.db.database import get_db
from app.middleware.security import SecurityMiddleware
from app.middleware.monitoring import MonitoringMiddleware
from app.middleware.geo_security import GeoSecurityMiddleware
from app.core.cache_manager import cache_manager
from app.core.performance_monitor import performance_monitor
from app.core.http_manager import startup_warmup, shutdown_connections

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
        # Verificar conexão com banco de dados
        db = next(get_db())
        db.execute(text("SELECT 1"))
        logger.info("Conexão com o banco de dados verificada com sucesso.")

        # Inicializar componentes de performance
        performance_monitor.start_monitoring()
        logger.info("Monitor de performance iniciado")

        # Warm-up da aplicação para reduzir cold start
        await startup_warmup()
        logger.info("Warm-up da aplicação concluído")

        # Inicializar tasks de limpeza periódica otimizada
        async def cleanup_task():
            while True:
                await asyncio.sleep(300)  # A cada 5 minutos
                try:
                    if hasattr(app.state, 'security_middleware'):
                        app.state.security_middleware.cleanup_old_data()
                    if hasattr(app.state, 'monitoring_middleware'):
                        app.state.monitoring_middleware.cleanup_old_data()

                    # Limpeza otimizada de caches
                    cache_manager.cleanup_expired()

                    # Limpeza de logs antigos (uma vez por dia)
                    import random
                    if random.randint(1, 288) == 1:  # 1/288 chance (5min * 288 = 24h)
                        from app.core.logger import cleanup_old_logs
                        cleanup_old_logs()

                except Exception as e:
                    logger.error(f"Erro na limpeza do middleware: {e}")

        asyncio.create_task(cleanup_task())
        logger.info("Tasks de limpeza otimizada iniciadas")

        logger.info("Inicialização completa")

    except Exception as e:
        logger.error(f"Erro na inicialização: {str(e)}")
        if not settings.DEBUG:
            raise  # Em produção, falhar se não conseguir conectar

    yield  # A aplicação executa aqui

    # Código de encerramento - executado quando a aplicação está sendo desligada
    logger.info("Encerrando a API MultasGO...")

    # Finalizar componentes
    performance_monitor.stop_monitoring()
    cache_manager.shutdown()
    shutdown_connections()

    logger.info("Componentes finalizados")

# Inicializar aplicação FastAPI com configurações otimizadas
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/docs" if settings.DEBUG else None,  # Desabilitar docs em produção
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
    # Configurações de performance
    generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}" if route.tags else route.name,
)

# Configuração para servir arquivos estáticos com cache otimizado
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.warning(f"Diretório de arquivos estáticos não encontrado: {STATIC_DIR}")

# Configuração para templates HTML com verificação
if os.path.exists(TEMPLATES_DIR):
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
else:
    logger.warning(f"Diretório de templates não encontrado: {TEMPLATES_DIR}")
    templates = None

# Adicionar middleware de monitoramento (PRIMEIRO - para capturar tudo)
monitoring_middleware = MonitoringMiddleware(app)
app.add_middleware(MonitoringMiddleware)
app.state.monitoring_middleware = monitoring_middleware

# Adicionar middleware de segurança geográfica (SEGUNDO - proteção anti-bot)
if not settings.DEBUG:  # Apenas em produção
    geo_security_middleware = GeoSecurityMiddleware(app, enable_geo_blocking=True)
    app.add_middleware(GeoSecurityMiddleware, enable_geo_blocking=True)
    app.state.geo_security_middleware = geo_security_middleware
    logger.info("Middleware de segurança geográfica ativado")

# Adicionar middleware de segurança básico (TERCEIRO - rate limiting)
security_middleware = SecurityMiddleware(
    app,
    rate_limit_requests=settings.RATE_LIMIT_REQUESTS,
    rate_limit_window=settings.RATE_LIMIT_WINDOW,
    block_duration=settings.BLOCK_DURATION,
    max_request_size=settings.MAX_REQUEST_SIZE,
    enable_bot_protection=settings.ENABLE_BOT_PROTECTION
)
app.add_middleware(SecurityMiddleware,
    rate_limit_requests=settings.RATE_LIMIT_REQUESTS,
    rate_limit_window=settings.RATE_LIMIT_WINDOW,
    block_duration=settings.BLOCK_DURATION,
    max_request_size=settings.MAX_REQUEST_SIZE,
    enable_bot_protection=settings.ENABLE_BOT_PROTECTION
)
app.state.security_middleware = security_middleware

# Middleware de hosts confiáveis (apenas em produção)
if not settings.DEBUG:
    trusted_hosts = ["localhost"] + [host.replace("*.", "") for host in settings.ALLOWED_HOSTS if host != "*"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

# Middleware de compressão
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configurar CORS de forma segura
cors_origins = settings.get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,  # Mais seguro
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Métodos específicos
    allow_headers=["Content-Type", "Authorization", "Accept", "Accept-Language"],  # Headers específicos
    max_age=3600,  # Cache preflight por 1 hora
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
    if templates is None:
        raise HTTPException(status_code=500, detail="Templates não configurados")
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/explorador", response_class=HTMLResponse)
async def explorador_page(request: Request):
    """
    Endpoint para a página do explorador de infrações.
    
    Retorna a interface web para explorar as infrações com filtros avançados.
    """
    if templates is None:
        raise HTTPException(status_code=500, detail="Templates não configurados")
    return templates.TemplateResponse("explorador.html", {"request": request})

@app.get("/noticias", response_class=HTMLResponse)
async def noticias_page(request: Request):
    """
    Endpoint para a página de notícias.

    Retorna a interface web com as notícias do MultasGO.
    """
    template_path = os.path.join(TEMPLATES_DIR, "noticias.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Página não encontrada")
    if templates is None:
        raise HTTPException(status_code=500, detail="Templates não configurados")
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

# Endpoints de debug e monitoramento (apenas em debug)
if settings.DEBUG:
    @app.get("/debug/security-stats")
    async def get_security_stats():
        """Retorna estatísticas do middleware de segurança (apenas em debug)."""
        if hasattr(app.state, 'security_middleware'):
            return app.state.security_middleware.get_security_stats()
        return {"error": "Security middleware not found"}

    @app.get("/debug/metrics")
    async def get_metrics():
        """Retorna métricas da aplicação (apenas em debug)."""
        metrics = {}

        if hasattr(app.state, 'monitoring_middleware'):
            metrics['monitoring'] = app.state.monitoring_middleware.get_metrics()

        if hasattr(app.state, 'security_middleware'):
            metrics['security'] = app.state.security_middleware.get_security_stats()

        if hasattr(app.state, 'geo_security_middleware'):
            metrics['geo_security'] = app.state.geo_security_middleware.get_geo_stats()

        # Performance e memória
        metrics['performance'] = performance_monitor.get_performance_report()

        # Cache
        metrics['cache'] = cache_manager.get_global_stats()

        # Estatísticas do banco de dados
        try:
            from app.db.database import get_db_stats
            metrics['database'] = get_db_stats()
        except Exception as e:
            metrics['database'] = {"error": str(e)}

        # Warm-up status
        try:
            from app.core.http_manager import warmup_manager
            metrics['warmup'] = warmup_manager.get_warmup_status()
        except Exception as e:
            metrics['warmup'] = {"error": str(e)}

        return metrics

    @app.post("/debug/reset-metrics")
    async def reset_metrics():
        """Reset das métricas (apenas em debug)."""
        if hasattr(app.state, 'monitoring_middleware'):
            app.state.monitoring_middleware.reset_metrics()
            return {"message": "Métricas resetadas"}
        return {"error": "Monitoring middleware not found"}

if __name__ == "__main__":
    import uvicorn

    # Configurações otimizadas para produção
    uvicorn_config = {
        "app": "app.main:app",
        "host": "0.0.0.0",
        "port": settings.PORT,
        "reload": settings.DEBUG,
        "access_log": settings.DEBUG,
        "server_header": False,  # Não expor servidor
        "date_header": False,    # Não expor data
    }

    # Configurações específicas para produção
    if not settings.DEBUG:
        uvicorn_config.update({
            "workers": settings.WORKERS,
            "log_level": "warning",
            "access_log": False,
        })

        # SSL se configurado
        if settings.SSL_CERTFILE and settings.SSL_KEYFILE:
            uvicorn_config.update({
                "ssl_certfile": settings.SSL_CERTFILE,
                "ssl_keyfile": settings.SSL_KEYFILE,
            })
            logger.info("SSL configurado - servidor HTTPS")

    logger.info(f"Iniciando servidor na porta {settings.PORT}")
    logger.info(f"Modo: {'Desenvolvimento' if settings.DEBUG else 'Produção'}")

    uvicorn.run(**uvicorn_config)