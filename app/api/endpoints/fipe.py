from fastapi import APIRouter, HTTPException, Query, status

from app.fipe.database import FipeDB
from app.fipe.ipva import ALIQUOTAS_IPVA, calcular_ipva

router = APIRouter(
    tags=["fipe"],
    responses={
        400: {"description": "Parametros invalidos"},
        404: {"description": "Dados nao encontrados"},
        500: {"description": "Erro interno"},
    },
)

TIPOS_VALIDOS = {"cars", "motorcycles", "trucks"}


def _validar_tipo(tipo: str) -> str:
    t = (tipo or "").strip().lower()
    if t not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo invalido. Use: cars, motorcycles ou trucks.",
        )
    return t


@router.get("/marcas")
def listar_marcas(tipo: str = Query("cars", description="cars, motorcycles ou trucks")):
    tipo = _validar_tipo(tipo)
    db = FipeDB()
    rows = db.listar_marcas(tipo=tipo)
    marcas = [r.get("marca") for r in rows if r.get("marca")]
    return {"tipo": tipo, "total": len(marcas), "marcas": marcas}


@router.get("/modelos")
def listar_modelos(
    marca: str = Query(..., min_length=1),
    tipo: str = Query("cars", description="cars, motorcycles ou trucks"),
):
    tipo = _validar_tipo(tipo)
    db = FipeDB()
    modelos = db.listar_modelos_por_marca(tipo=tipo, marca=marca)
    lista = [m["modelo"] for m in modelos]
    return {"tipo": tipo, "marca": marca, "total": len(lista), "modelos": lista}


@router.get("/anos")
def listar_anos(
    marca: str = Query(..., min_length=1),
    modelo: str = Query(..., min_length=1),
    tipo: str = Query("cars", description="cars, motorcycles ou trucks"),
):
    tipo = _validar_tipo(tipo)
    db = FipeDB()
    anos = db.listar_anos_por_modelo(tipo=tipo, marca=marca, modelo=modelo)
    lista = [a["ano"] for a in anos]
    return {"tipo": tipo, "marca": marca, "modelo": modelo, "total": len(lista), "anos": lista}


@router.get("/ipva")
def calcular_ipva_endpoint(
    estado: str = Query(..., min_length=2, max_length=2, description="UF ex: SP"),
    marca: str = Query(..., min_length=1),
    modelo: str = Query(..., min_length=1),
    ano: int = Query(..., ge=1900, le=2100),
    tipo: str = Query("cars", description="cars, motorcycles ou trucks"),
):
    tipo = _validar_tipo(tipo)
    uf = estado.strip().upper()
    if uf not in ALIQUOTAS_IPVA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado invalido para IPVA: {estado}",
        )

    db = FipeDB()
    veiculo = db.buscar_preco(tipo=tipo, marca=marca, modelo=modelo, ano=ano)
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preco FIPE nao encontrado para os filtros informados.",
        )

    preco_valor = float(veiculo.get("preco_valor") or 0.0)
    if preco_valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valor FIPE indisponivel para os filtros informados.",
        )

    ipva = calcular_ipva(preco_valor, uf)
    return {
        "tipo": tipo,
        "estado": uf,
        "veiculo": {
            "marca": veiculo.get("marca"),
            "modelo": veiculo.get("modelo"),
            "ano": int(veiculo.get("ano_modelo") or ano),
            "combustivel": veiculo.get("combustivel"),
            "codigo_fipe": veiculo.get("codigo_fipe"),
            "mes_referencia": veiculo.get("mes_referencia"),
            "preco_fipe": veiculo.get("preco"),
            "preco_fipe_valor": preco_valor,
        },
        "ipva": ipva,
    }
