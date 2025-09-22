"""
Cache Manager Inteligente para MultasGO - Solução para Memory Leaks
Controla uso de memória, TTL e limpeza automática de caches.
"""
import time
import gc
import psutil
import threading
from typing import Dict, Any, Optional, Callable
from collections import OrderedDict
from dataclasses import dataclass
from functools import wraps

from app.core.config import settings
from app.core.logger import logger


@dataclass
class CacheEntry:
    """Entrada de cache com metadados."""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    memory_size: int


class SmartCache:
    """
    Cache inteligente com controle de memória e TTL.

    Features:
    - Limite de memória configurável
    - TTL por entrada
    - LRU eviction
    - Estatísticas de uso
    - Limpeza automática
    """

    def __init__(self,
                 max_memory_mb: int = 100,
                 default_ttl: int = 300,
                 cleanup_interval: int = 1800):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._memory_usage = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._last_cleanup = time.time()

        logger.info(f"SmartCache inicializado - Limite: {max_memory_mb}MB, TTL: {default_ttl}s")

    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]
            current_time = time.time()

            # Verificar TTL
            if current_time - entry.created_at > self.default_ttl:
                self._remove_entry(key)
                self._misses += 1
                return None

            # Atualizar acesso
            entry.last_accessed = current_time
            entry.access_count += 1
            self._hits += 1

            # Mover para o final (LRU)
            self._cache.move_to_end(key)

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Armazena valor no cache."""
        if ttl is None:
            ttl = self.default_ttl

        # Estimar tamanho da memória
        memory_size = self._estimate_size(value)

        with self._lock:
            current_time = time.time()

            # Remover entrada existente se houver
            if key in self._cache:
                self._remove_entry(key)

            # Verificar se caberia no cache
            if memory_size > self.max_memory_bytes:
                logger.warning(f"Objeto muito grande para cache: {memory_size} bytes")
                return

            # Liberar espaço se necessário
            while (self._memory_usage + memory_size > self.max_memory_bytes and
                   len(self._cache) > 0):
                self._evict_lru()

            # Adicionar nova entrada
            entry = CacheEntry(
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                access_count=0,
                memory_size=memory_size
            )

            self._cache[key] = entry
            self._memory_usage += memory_size

            # Limpeza periódica
            if current_time - self._last_cleanup > self.cleanup_interval:
                self._cleanup_expired()

    def delete(self, key: str) -> bool:
        """Remove entrada do cache."""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False

    def clear(self) -> None:
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()
            self._memory_usage = 0
            gc.collect()
            logger.info("Cache completamente limpo")

    def _remove_entry(self, key: str) -> None:
        """Remove entrada e atualiza métricas."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._memory_usage -= entry.memory_size

    def _evict_lru(self) -> None:
        """Remove a entrada menos recentemente usada."""
        if self._cache:
            key, _ = self._cache.popitem(last=False)  # Remove o primeiro (LRU)
            self._evictions += 1
            logger.debug(f"Entrada LRU removida: {key}")

    def _cleanup_expired(self) -> None:
        """Remove entradas expiradas."""
        current_time = time.time()
        expired_keys = []

        for key, entry in self._cache.items():
            if current_time - entry.created_at > self.default_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            self._remove_entry(key)

        if expired_keys:
            logger.info(f"Limpeza: {len(expired_keys)} entradas expiradas removidas")

        self._last_cleanup = current_time
        gc.collect()  # Força garbage collection

    def _estimate_size(self, obj: Any) -> int:
        """Estima o tamanho em bytes de um objeto."""
        try:
            import sys
            if hasattr(obj, '__dict__'):
                return sys.getsizeof(obj) + sum(sys.getsizeof(v) for v in obj.__dict__.values())
            return sys.getsizeof(obj)
        except:
            return 1024  # Estimativa padrão de 1KB

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "entries": len(self._cache),
                "memory_usage_mb": round(self._memory_usage / 1024 / 1024, 2),
                "memory_limit_mb": round(self.max_memory_bytes / 1024 / 1024, 2),
                "memory_usage_percent": round(self._memory_usage / self.max_memory_bytes * 100, 2),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self._evictions,
                "last_cleanup": self._last_cleanup
            }


class CacheManager:
    """
    Gerenciador global de caches da aplicação.
    """

    def __init__(self):
        self.caches: Dict[str, SmartCache] = {}
        self._monitor_thread = None
        self._monitoring = False

        # Criar caches padrão
        self.search_cache = self.create_cache(
            "search",
            max_memory_mb=settings.MAX_CACHE_MEMORY_MB // 2,  # 50% para search
            default_ttl=settings.CACHE_TTL
        )

        self.data_cache = self.create_cache(
            "data",
            max_memory_mb=settings.MAX_CACHE_MEMORY_MB // 4,  # 25% para data
            default_ttl=settings.CACHE_TTL * 2
        )

        self.api_cache = self.create_cache(
            "api",
            max_memory_mb=settings.MAX_CACHE_MEMORY_MB // 4,  # 25% para API
            default_ttl=settings.CACHE_TTL
        )

        self.start_monitoring()

    def create_cache(self, name: str, **kwargs) -> SmartCache:
        """Cria um novo cache nomeado."""
        cache = SmartCache(**kwargs)
        self.caches[name] = cache
        logger.info(f"Cache '{name}' criado")
        return cache

    def get_cache(self, name: str) -> Optional[SmartCache]:
        """Obtém cache por nome."""
        return self.caches.get(name)

    def start_monitoring(self):
        """Inicia monitoramento de memória."""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_memory, daemon=True)
        self._monitor_thread.start()
        logger.info("Monitoramento de cache iniciado")

    def _monitor_memory(self):
        """Thread de monitoramento de memória."""
        while self._monitoring:
            try:
                # Verificar uso de memória do sistema
                memory_percent = psutil.virtual_memory().percent

                if memory_percent > 90:  # Se memória > 90%
                    logger.warning(f"Memória alta: {memory_percent}% - Limpando caches")
                    self.emergency_cleanup()
                elif memory_percent > 80:  # Se memória > 80%
                    logger.info(f"Memória moderada: {memory_percent}% - Limpeza preventiva")
                    self.cleanup_expired()

                time.sleep(60)  # Verificar a cada minuto

            except Exception as e:
                logger.error(f"Erro no monitoramento de cache: {e}")
                time.sleep(300)  # Esperar 5 minutos em caso de erro

    def cleanup_expired(self):
        """Limpa entradas expiradas de todos os caches."""
        for name, cache in self.caches.items():
            cache._cleanup_expired()

        gc.collect()
        logger.info("Limpeza preventiva de caches executada")

    def emergency_cleanup(self):
        """Limpeza emergencial - remove 50% das entradas de cada cache."""
        for name, cache in self.caches.items():
            with cache._lock:
                entries_to_remove = len(cache._cache) // 2
                for _ in range(entries_to_remove):
                    if cache._cache:
                        cache._evict_lru()

        gc.collect()
        logger.warning("Limpeza emergencial de caches executada")

    def get_global_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de todos os caches."""
        stats = {}
        total_memory = 0
        total_entries = 0

        for name, cache in self.caches.items():
            cache_stats = cache.get_stats()
            stats[name] = cache_stats
            total_memory += cache_stats["memory_usage_mb"]
            total_entries += cache_stats["entries"]

        try:
            system_memory = psutil.virtual_memory()
            stats["system"] = {
                "total_cache_memory_mb": round(total_memory, 2),
                "total_entries": total_entries,
                "system_memory_percent": system_memory.percent,
                "system_memory_available_mb": round(system_memory.available / 1024 / 1024, 2)
            }
        except:
            stats["system"] = {"error": "Não foi possível obter estatísticas do sistema"}

        return stats

    def shutdown(self):
        """Para o monitoramento e limpa caches."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        for cache in self.caches.values():
            cache.clear()

        logger.info("CacheManager finalizado")


# Cache decorator melhorado
def smart_cache(cache_name: str = "data", ttl: Optional[int] = None):
    """
    Decorator para cache inteligente de funções.

    Args:
        cache_name: Nome do cache a usar
        ttl: Time-to-live em segundos (usa padrão do cache se None)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave única baseada em função e argumentos
            try:
                # Converter listas para tuplas para permitir hash
                hashable_args = tuple(
                    tuple(arg) if isinstance(arg, list) else arg for arg in args
                )
                hashable_kwargs = tuple(
                    (k, tuple(v) if isinstance(v, list) else v)
                    for k, v in sorted(kwargs.items())
                )
                key = f"{func.__name__}:{hash((hashable_args, hashable_kwargs))}"
            except (TypeError, ValueError):
                # Se não conseguir fazer hash, usar string dos argumentos
                key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            cache = cache_manager.get_cache(cache_name)
            if not cache:
                # Se cache não existir, executar função normalmente
                return func(*args, **kwargs)

            # Tentar obter do cache
            result = cache.get(key)
            if result is not None:
                return result

            # Executar função e armazenar resultado
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)

            return result

        return wrapper
    return decorator


# Instância global do gerenciador de cache
cache_manager = CacheManager()