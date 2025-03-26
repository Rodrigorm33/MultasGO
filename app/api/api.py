from fastapi import APIRouter
from app.api.endpoints import infracoes
from app.core.config import settings

api_router = APIRouter()

# Endpoint para a rota raiz da API v1
@api_router.get("/", 
    tags=["recursos-api"],
    summary="Informações da API MultasGO",
    description="Retorna metadados completos sobre a API MultasGO, incluindo versão, endpoints disponíveis e status do serviço.",
    response_description="Informações detalhadas da API e seus endpoints")
def api_v1_root():
    """
    Retorna informações detalhadas sobre a API MultasGO.
    
    Este endpoint fornece:
    - Dados do projeto como nome, versão e descrição
    - Lista de todos os endpoints disponíveis com descrições
    - Links para documentação e verificação de status
    """
    return {
        "api": settings.PROJECT_NAME,
        "versao": settings.PROJECT_VERSION,
        "descricao": settings.PROJECT_DESCRIPTION,
        "endpoints": {
            "infrações": {
                "listar": "/api/v1/infracoes/",
                "pesquisar": "/api/v1/infracoes/pesquisa",
                "detalhe": "/api/v1/infracoes/{codigo}"
            },
            "sistema": {
                "health_check": "/health",
                "root": "/"
            }
        },
        "documentacao": "/docs",
        "status": "online"
    }

# Incluir os endpoints de infrações
api_router.include_router(
    infracoes.router,
    prefix="/infracoes",
    tags=["infrações"]
)