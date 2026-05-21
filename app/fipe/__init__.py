# app/fipe/ - Módulo de consulta Tabela FIPE
# Crawler + banco SQLite local

from app.fipe.database import FipeDB
from app.fipe.crawler import FipeCrawler
from app.fipe.ipva import calcular_ipva, ALIQUOTAS_IPVA

__all__ = ["FipeDB", "FipeCrawler", "calcular_ipva", "ALIQUOTAS_IPVA"]
