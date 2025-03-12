from fastapi import APIRouter
from app.api.endpoints import infracoes

api_router = APIRouter()

# Incluir os endpoints de infrações
api_router.include_router(
    infracoes.router,
    prefix="/infracoes",
    tags=["infrações"]
)
) 