from fastapi import APIRouter

from app.api.endpoints import fipe, infracoes
from app.core.config import settings

api_router = APIRouter()


@api_router.get(
    "/",
    tags=["recursos-api"],
    summary="Informacoes da API MultasGO",
    description="Retorna metadados completos sobre a API MultasGO.",
    response_description="Informacoes detalhadas da API e seus endpoints",
)
def api_v1_root():
    return {
        "api": settings.PROJECT_NAME,
        "versao": settings.PROJECT_VERSION,
        "descricao": settings.PROJECT_DESCRIPTION,
        "endpoints": {
            "infracoes": {
                "listar": "/api/v1/infracoes/",
                "pesquisar": "/api/v1/infracoes/pesquisa",
                "detalhe": "/api/v1/infracoes/{codigo}",
            },
            "fipe": {
                "marcas": "/api/v1/fipe/marcas?tipo=cars",
                "modelos": "/api/v1/fipe/modelos?marca=Audi&tipo=cars",
                "anos": "/api/v1/fipe/anos?marca=Audi&modelo=A3&tipo=cars",
                "ipva": "/api/v1/fipe/ipva?estado=SP&marca=Audi&modelo=A3&ano=2020&tipo=cars",
            },
            "sistema": {"health_check": "/health", "root": "/"},
        },
        "documentacao": "/docs",
        "status": "online",
    }


api_router.include_router(
    infracoes.router,
    prefix="/infracoes",
    tags=["infracoes"],
)

api_router.include_router(
    fipe.router,
    prefix="/fipe",
    tags=["fipe"],
)
