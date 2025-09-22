"""
Monitor de Performance Avançado - Solução para RAM 100% e Memory Leaks
Monitora uso de memória, detecta vazamentos e otimiza performance automaticamente.
"""
import time
import gc
import psutil
import threading
import tracemalloc
from typing import Dict, Any, List, Optional
from collections import deque, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.logger import logger


@dataclass
class MemorySnapshot:
    """Snapshot de uso de memória."""
    timestamp: float
    total_mb: float
    available_mb: float
    percent: float
    process_mb: float
    cache_mb: float


@dataclass
class PerformanceMetrics:
    """Métricas de performance por endpoint."""
    endpoint: str
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    total_requests: int
    error_count: int
    memory_usage_mb: float


class PerformanceMonitor:
    """
    Monitor de performance com foco em vazamentos de memória e otimização.

    Features:
    - Detecção de memory leaks
    - Garbage collection automático
    - Alertas de uso de memória
    - Otimização de cache
    - Estatísticas detalhadas por endpoint
    """

    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None

        # Histórico de memória (últimas 1000 amostras)
        self.memory_history: deque = deque(maxlen=1000)

        # Métricas por endpoint
        self.endpoint_metrics: Dict[str, PerformanceMetrics] = {}

        # Controles de otimização
        self.last_gc_time = time.time()
        self.last_cache_cleanup = time.time()
        self.gc_frequency = 300  # 5 minutos
        self.cache_cleanup_frequency = 600  # 10 minutos

        # Thresholds de alerta
        self.memory_warning_threshold = 80  # 80%
        self.memory_critical_threshold = 90  # 90%
        self.memory_emergency_threshold = 95  # 95%

        # Estatísticas de otimização
        self.optimization_stats = {
            "gc_runs": 0,
            "cache_cleanups": 0,
            "memory_alerts": 0,
            "emergency_cleanups": 0
        }

        # Inicializar tracemalloc se disponível
        if not tracemalloc.is_tracing():
            try:
                tracemalloc.start()
                logger.info("Memory tracing iniciado")
            except:
                logger.warning("Não foi possível iniciar memory tracing")

    def start_monitoring(self):
        """Inicia monitoramento contínuo."""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Monitor de performance iniciado")

    def stop_monitoring(self):
        """Para o monitoramento."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Monitor de performance parado")

    def _monitor_loop(self):
        """Loop principal de monitoramento."""
        while self.monitoring:
            try:
                # Capturar snapshot de memória
                self._capture_memory_snapshot()

                # Verificar se precisa de otimizações
                self._check_optimization_needs()

                # Verificar vazamentos de memória
                self._check_memory_leaks()

                # Sleep adaptativo baseado no uso de memória
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 90:
                    sleep_time = 30  # Monitorar mais frequentemente quando crítico
                elif memory_percent > 80:
                    sleep_time = 60  # Monitorar frequentemente quando alto
                else:
                    sleep_time = 120  # Monitorar normalmente

                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Erro no monitor de performance: {e}")
                time.sleep(300)  # Aguardar 5 minutos em caso de erro

    def _capture_memory_snapshot(self):
        """Captura snapshot atual de memória."""
        try:
            # Estatísticas do sistema
            system_memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()

            # Tentar obter uso do cache (se disponível)
            cache_mb = 0
            try:
                from app.core.cache_manager import cache_manager
                cache_stats = cache_manager.get_global_stats()
                cache_mb = cache_stats.get("system", {}).get("total_cache_memory_mb", 0)
            except:
                pass

            snapshot = MemorySnapshot(
                timestamp=time.time(),
                total_mb=round(system_memory.total / 1024 / 1024, 2),
                available_mb=round(system_memory.available / 1024 / 1024, 2),
                percent=system_memory.percent,
                process_mb=round(process_memory.rss / 1024 / 1024, 2),
                cache_mb=cache_mb
            )

            self.memory_history.append(snapshot)

            # Log de alertas baseado no uso
            if snapshot.percent >= self.memory_emergency_threshold:
                logger.critical(f"MEMÓRIA CRÍTICA: {snapshot.percent}% - Iniciando limpeza emergencial")
                self._emergency_memory_cleanup()
            elif snapshot.percent >= self.memory_critical_threshold:
                logger.error(f"Memória muito alta: {snapshot.percent}% - Processo: {snapshot.process_mb}MB")
                self.optimization_stats["memory_alerts"] += 1
            elif snapshot.percent >= self.memory_warning_threshold:
                logger.warning(f"Memória alta: {snapshot.percent}% - Processo: {snapshot.process_mb}MB")

        except Exception as e:
            logger.error(f"Erro ao capturar snapshot de memória: {e}")

    def _check_optimization_needs(self):
        """Verifica se precisa executar otimizações."""
        current_time = time.time()

        # Garbage collection automático
        if current_time - self.last_gc_time > self.gc_frequency:
            self._run_garbage_collection()

        # Limpeza de cache automática
        if current_time - self.last_cache_cleanup > self.cache_cleanup_frequency:
            self._cleanup_caches()

    def _check_memory_leaks(self):
        """Detecta possíveis vazamentos de memória."""
        if len(self.memory_history) < 10:
            return

        # Analisar tendência de memória nas últimas 10 amostras
        recent_samples = list(self.memory_history)[-10:]
        memory_trend = [sample.process_mb for sample in recent_samples]

        # Calcular taxa de crescimento
        if len(memory_trend) >= 2:
            growth_rate = (memory_trend[-1] - memory_trend[0]) / len(memory_trend)

            # Se a memória está crescendo consistentemente
            if growth_rate > 10:  # Mais de 10MB por amostra
                logger.warning(f"Possível memory leak detectado - Taxa de crescimento: {growth_rate:.2f}MB/sample")

                # Forçar garbage collection mais agressivo
                self._aggressive_cleanup()

    def _run_garbage_collection(self):
        """Executa garbage collection otimizado."""
        try:
            before_mb = psutil.Process().memory_info().rss / 1024 / 1024

            # Garbage collection em múltiplas gerações
            collected = gc.collect()

            after_mb = psutil.Process().memory_info().rss / 1024 / 1024
            freed_mb = before_mb - after_mb

            self.optimization_stats["gc_runs"] += 1
            self.last_gc_time = time.time()

            if freed_mb > 1:  # Se liberou mais de 1MB
                logger.info(f"GC executado - Liberado: {freed_mb:.2f}MB, Objetos coletados: {collected}")

        except Exception as e:
            logger.error(f"Erro no garbage collection: {e}")

    def _cleanup_caches(self):
        """Executa limpeza de caches."""
        try:
            # Limpeza do cache manager
            try:
                from app.core.cache_manager import cache_manager
                cache_manager.cleanup_expired()
                self.optimization_stats["cache_cleanups"] += 1
                logger.debug("Cache cleanup executado")
            except Exception as e:
                logger.debug(f"Erro na limpeza do cache manager: {e}")

            # Limpeza do cache de busca
            try:
                from app.services import search_service
                search_service.limpar_cache_palavras()
                logger.debug("Cache de busca limpo")
            except Exception as e:
                logger.debug(f"Erro na limpeza do cache de busca: {e}")

            self.last_cache_cleanup = time.time()

        except Exception as e:
            logger.error(f"Erro na limpeza de caches: {e}")

    def _aggressive_cleanup(self):
        """Limpeza agressiva para situações de memory leak."""
        try:
            logger.warning("Executando limpeza agressiva de memória")

            # 1. Múltiplos rounds de GC
            for _ in range(3):
                gc.collect()

            # 2. Limpeza forçada de caches
            try:
                from app.core.cache_manager import cache_manager
                cache_manager.emergency_cleanup()
            except:
                pass

            # 3. Limpar cache de busca
            try:
                from app.services import search_service
                search_service.limpar_cache_palavras()
            except:
                pass

            # 4. Força limpeza de objetos não referenciados
            import weakref
            weakref.WeakSet().clear()

            logger.info("Limpeza agressiva concluída")

        except Exception as e:
            logger.error(f"Erro na limpeza agressiva: {e}")

    def _emergency_memory_cleanup(self):
        """Limpeza emergencial quando memória está crítica."""
        try:
            logger.critical("EXECUTANDO LIMPEZA EMERGENCIAL DE MEMÓRIA")
            self.optimization_stats["emergency_cleanups"] += 1

            # 1. Limpeza agressiva
            self._aggressive_cleanup()

            # 2. Limpar histórico de monitoramento (manter apenas últimos 100)
            if len(self.memory_history) > 100:
                # Manter apenas os 100 mais recentes
                recent_history = list(self.memory_history)[-100:]
                self.memory_history.clear()
                self.memory_history.extend(recent_history)

            # 3. Reset de estatísticas antigas
            current_time = time.time()
            self.last_gc_time = current_time
            self.last_cache_cleanup = current_time

            logger.critical("Limpeza emergencial concluída")

        except Exception as e:
            logger.critical(f"ERRO NA LIMPEZA EMERGENCIAL: {e}")

    def record_endpoint_metrics(self, endpoint: str, response_time: float,
                              status_code: int, memory_usage_mb: float):
        """Registra métricas de performance de um endpoint."""
        if endpoint not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint] = PerformanceMetrics(
                endpoint=endpoint,
                avg_response_time=response_time,
                min_response_time=response_time,
                max_response_time=response_time,
                total_requests=1,
                error_count=1 if status_code >= 400 else 0,
                memory_usage_mb=memory_usage_mb
            )
        else:
            metrics = self.endpoint_metrics[endpoint]

            # Atualizar métricas
            total = metrics.total_requests + 1
            metrics.avg_response_time = (
                (metrics.avg_response_time * metrics.total_requests + response_time) / total
            )
            metrics.min_response_time = min(metrics.min_response_time, response_time)
            metrics.max_response_time = max(metrics.max_response_time, response_time)
            metrics.total_requests = total

            if status_code >= 400:
                metrics.error_count += 1

            # Média móvel do uso de memória
            metrics.memory_usage_mb = (metrics.memory_usage_mb + memory_usage_mb) / 2

    def get_performance_report(self) -> Dict[str, Any]:
        """Gera relatório completo de performance."""
        current_memory = psutil.virtual_memory()
        process_memory = psutil.Process().memory_info()

        # Estatísticas de memória
        memory_stats = {
            "current": {
                "system_percent": current_memory.percent,
                "system_total_gb": round(current_memory.total / 1024 / 1024 / 1024, 2),
                "system_available_gb": round(current_memory.available / 1024 / 1024 / 1024, 2),
                "process_mb": round(process_memory.rss / 1024 / 1024, 2)
            },
            "history_samples": len(self.memory_history)
        }

        # Análise de tendência se temos histórico suficiente
        if len(self.memory_history) >= 10:
            recent_samples = list(self.memory_history)[-10:]
            memory_trend = [s.process_mb for s in recent_samples]

            memory_stats["trend"] = {
                "avg_process_mb": round(sum(memory_trend) / len(memory_trend), 2),
                "min_process_mb": round(min(memory_trend), 2),
                "max_process_mb": round(max(memory_trend), 2),
                "growth_rate_mb": round((memory_trend[-1] - memory_trend[0]) / len(memory_trend), 2)
            }

        # Top endpoints por uso de memória
        memory_heavy_endpoints = sorted(
            [(k, v.memory_usage_mb) for k, v in self.endpoint_metrics.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Top endpoints mais lentos
        slow_endpoints = sorted(
            [(k, v.avg_response_time) for k, v in self.endpoint_metrics.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "memory": memory_stats,
            "optimization": self.optimization_stats,
            "endpoints": {
                "total_tracked": len(self.endpoint_metrics),
                "memory_heavy": memory_heavy_endpoints,
                "slowest": slow_endpoints
            },
            "monitoring": {
                "active": self.monitoring,
                "last_gc": self.last_gc_time,
                "last_cache_cleanup": self.last_cache_cleanup
            }
        }

    def get_memory_usage_chart_data(self, last_hours: int = 1) -> List[Dict[str, Any]]:
        """Retorna dados para gráfico de uso de memória."""
        cutoff_time = time.time() - (last_hours * 3600)

        chart_data = []
        for snapshot in self.memory_history:
            if snapshot.timestamp >= cutoff_time:
                chart_data.append({
                    "timestamp": datetime.fromtimestamp(snapshot.timestamp).isoformat(),
                    "system_percent": snapshot.percent,
                    "process_mb": snapshot.process_mb,
                    "cache_mb": snapshot.cache_mb
                })

        return chart_data


# Instância global do monitor
performance_monitor = PerformanceMonitor()