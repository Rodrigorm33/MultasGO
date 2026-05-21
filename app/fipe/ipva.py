"""
Calculo de IPVA por estado (UF) com base no valor FIPE.
"""

from typing import Dict


ALIQUOTAS_IPVA: Dict[str, float] = {
    "AC": 0.02,
    "AL": 0.03,
    "AM": 0.03,
    "AP": 0.03,
    "BA": 0.025,
    "CE": 0.03,
    "DF": 0.035,
    "ES": 0.02,
    "GO": 0.0375,
    "MA": 0.025,
    "MG": 0.04,
    "MS": 0.035,
    "MT": 0.03,
    "PA": 0.025,
    "PB": 0.025,
    "PE": 0.03,
    "PI": 0.025,
    "PR": 0.035,
    "RJ": 0.04,
    "RN": 0.03,
    "RO": 0.03,
    "RR": 0.03,
    "RS": 0.03,
    "SC": 0.02,
    "SE": 0.025,
    "SP": 0.04,
    "TO": 0.02,
}


def calcular_ipva(valor_fipe: float, estado: str) -> dict:
    uf = (estado or "").strip().upper()
    if uf not in ALIQUOTAS_IPVA:
        raise ValueError(f"Estado invalido para IPVA: {estado}")

    aliquota = ALIQUOTAS_IPVA[uf]
    ipva_total = float(valor_fipe) * aliquota

    # Parcelamento padrao em 3 vezes (estimativa informativa).
    parcela_base = round(ipva_total / 3, 2)
    parcelas = [parcela_base, parcela_base, round(ipva_total - (parcela_base * 2), 2)]

    return {
        "estado": uf,
        "aliquota": aliquota,
        "aliquota_percentual": round(aliquota * 100, 2),
        "ipva_total": round(ipva_total, 2),
        "parcelas": [
            {"numero": 1, "valor": parcelas[0]},
            {"numero": 2, "valor": parcelas[1]},
            {"numero": 3, "valor": parcelas[2]},
        ],
    }
