"""
HTTP Connection Pool Manager - Solução para Cold Start e Performance
Gerencia conexões HTTP reutilizáveis e warm-up da aplicação.
"""
import asyncio
import time
from typing import Dict, Any, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings
from app.core.logger import logger


class HTTPManager:
    """
    Gerenciador de conexões HTTP com pool e retry automático.
    Resolve problemas de cold start e conectividade.
    """

    def __init__(self):
        self.session = None
        self._initialized = False
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0,
            "last_request_time": 0
        }

    def initialize(self):
        """Inicializa sessão HTTP com pool de conexões."""
        if self._initialized:
            return

        try:
            self.session = requests.Session()

            # Configurar pool de conexões
            adapter = HTTPAdapter(
                pool_connections=settings.HTTP_POOL_CONNECTIONS,
                pool_maxsize=settings.HTTP_POOL_MAXSIZE,
                max_retries=Retry(
                    total=3,
                    backoff_factor=0.3,
                    status_forcelist=[500, 502, 503, 504, 429]
                )
            )

            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

            # Headers padrão
            self.session.headers.update({
                "User-Agent": f"MultasGO/{settings.PROJECT_VERSION}",
                "Accept": "application/json",
                "Connection": "keep-alive"
            })

            # Timeout padrão
            self.session.timeout = settings.HTTP_TIMEOUT

            self._initialized = True
            logger.info("HTTPManager inicializado com pool de conexões")

        except Exception as e:
            logger.error(f"Erro ao inicializar HTTPManager: {e}")
            # Fallback para requests simples
            self.session = requests

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET request com estatísticas."""
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """POST request com estatísticas."""
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Executa request e atualiza estatísticas."""
        start_time = time.time()

        try:
            if not self._initialized:
                self.initialize()

            response = self.session.request(method, url, **kwargs)

            # Atualizar estatísticas
            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return response

        except Exception as e:
            response_time = time.time() - start_time
            self._update_stats(False, response_time)
            logger.error(f"HTTP {method} error para {url}: {e}")
            raise

    def _update_stats(self, success: bool, response_time: float):
        """Atualiza estatísticas de performance."""
        self._stats["total_requests"] += 1
        if success:
            self._stats["successful_requests"] += 1
        else:
            self._stats["failed_requests"] += 1

        # Calcular média móvel do tempo de resposta
        if self._stats["total_requests"] == 1:
            self._stats["avg_response_time"] = response_time
        else:
            self._stats["avg_response_time"] = (
                (self._stats["avg_response_time"] * (self._stats["total_requests"] - 1) + response_time)
                / self._stats["total_requests"]
            )

        self._stats["last_request_time"] = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas HTTP."""
        success_rate = 0
        if self._stats["total_requests"] > 0:
            success_rate = (self._stats["successful_requests"] / self._stats["total_requests"]) * 100

        return {
            **self._stats,
            "success_rate_percent": round(success_rate, 2),
            "avg_response_time_ms": round(self._stats["avg_response_time"] * 1000, 2),
            "initialized": self._initialized
        }

    def close(self):
        """Fecha sessão HTTP."""
        if self.session and hasattr(self.session, 'close'):
            self.session.close()
        self._initialized = False
        logger.info("HTTPManager finalizado")


class WarmupManager:
    """
    Gerenciador de warm-up da aplicação.
    Executa consultas iniciais para pré-carregar caches e conexões.
    """

    def __init__(self):
        self.warmup_completed = False
        self.warmup_start_time = 0
        self.warmup_duration = 0

    async def perform_warmup(self):
        """
        Executa warm-up da aplicação para reduzir cold start.
        """
        if not settings.ENABLE_WARMUP or self.warmup_completed:
            return

        logger.info("Iniciando warm-up da aplicação...")
        self.warmup_start_time = time.time()

        try:
            # 1. Warm-up do banco de dados
            await self._warmup_database()

            # 2. Warm-up do cache de busca
            await self._warmup_search_cache()

            # 3. Warm-up das conexões HTTP
            await self._warmup_http_connections()

            # 4. Pré-carregar dados frequentes
            await self._preload_frequent_data()

            self.warmup_duration = time.time() - self.warmup_start_time
            self.warmup_completed = True

            logger.info(f"Warm-up concluído em {self.warmup_duration:.2f}s")

        except Exception as e:
            logger.error(f"Erro durante warm-up: {e}")
            self.warmup_completed = True  # Continuar mesmo com erro

    async def _warmup_database(self):
        """Warm-up das conexões de banco."""
        try:
            from app.db.database import get_db_context
            with get_db_context() as db:
                # Consultas simples para ativar o pool
                from sqlalchemy import text
                db.execute(text("SELECT COUNT(*) FROM bdbautos"))
                logger.debug("Warm-up do banco de dados concluído")
        except Exception as e:
            logger.warning(f"Erro no warm-up do banco: {e}")

    async def _warmup_search_cache(self):
        """Pré-carrega cache de busca com consultas comuns."""
        try:
            from app.services import search_service

            # Buscar palavras comuns definidas na configuração
            for query in settings.WARMUP_QUERIES:
                if query.strip():
                    try:
                        with get_db_context() as db:
                            # Simular busca sem retornar resultados grandes
                            search_service.buscar_infracoes(
                                db=db,
                                termo_busca=query.strip(),
                                limite_resultados=5
                            )
                            await asyncio.sleep(0.1)  # Pequena pausa
                    except Exception as e:
                        logger.debug(f"Erro no warm-up da busca '{query}': {e}")

            logger.debug("Warm-up do cache de busca concluído")

        except Exception as e:
            logger.warning(f"Erro no warm-up da busca: {e}")

    async def _warmup_http_connections(self):
        """Inicializa pool de conexões HTTP."""
        try:
            http_manager.initialize()
            logger.debug("Warm-up das conexões HTTP concluído")
        except Exception as e:
            logger.warning(f"Erro no warm-up HTTP: {e}")

    async def _preload_frequent_data(self):
        """Pré-carrega dados frequentemente acessados."""
        try:
            from app.db.database import get_db_context
            from sqlalchemy import text

            with get_db_context() as db:
                # Carregar estatísticas básicas
                db.execute(text("""
                    SELECT "Gravidade", COUNT(*)
                    FROM bdbautos
                    GROUP BY "Gravidade"
                """))

                # Carregar códigos mais comuns
                db.execute(text("""
                    SELECT "Código de Infração", "Infração"
                    FROM bdbautos
                    ORDER BY "Código de Infração"
                    LIMIT 50
                """))

            logger.debug("Pré-carregamento de dados concluído")

        except Exception as e:
            logger.warning(f"Erro no pré-carregamento: {e}")

    def get_warmup_status(self) -> Dict[str, Any]:
        """Retorna status do warm-up."""
        return {
            "completed": self.warmup_completed,
            "duration_seconds": round(self.warmup_duration, 2) if self.warmup_completed else 0,
            "enabled": settings.ENABLE_WARMUP
        }


# Instâncias globais
http_manager = HTTPManager()
warmup_manager = WarmupManager()


# Função para usar em lifespan
async def startup_warmup():
    """Função para chamar no startup da aplicação."""
    await warmup_manager.perform_warmup()


def shutdown_connections():
    """Função para chamar no shutdown da aplicação."""
    http_manager.close()