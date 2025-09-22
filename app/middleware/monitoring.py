"""
Middleware de monitoramento para performance e métricas da aplicação.
"""
import time
import uuid
from typing import Dict, List
from collections import defaultdict, deque
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from app.core.logger import log_api_access, log_performance, log_security_event

class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware para monitoramento de performance, logging de acesso e métricas.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger('MultasGO.monitoring')

        # Métricas em memória
        self.request_count = 0
        self.error_count = 0
        self.response_times = deque(maxlen=1000)  # Últimas 1000 requisições
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'avg_time': 0,
            'min_time': float('inf'),
            'max_time': 0,
            'error_count': 0
        })

        # Status codes tracking
        self.status_codes = defaultdict(int)

        # IPs suspeitos
        self.suspicious_ips = defaultdict(lambda: {
            'requests': 0,
            'errors': 0,
            'last_request': 0
        })

    def get_client_ip(self, request: Request) -> str:
        """Obtém o IP real do cliente."""
        forwarded_ips = request.headers.get("x-forwarded-for")
        if forwarded_ips:
            return forwarded_ips.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"

    def is_health_check(self, path: str) -> bool:
        """Verifica se é um health check (não logar como requisição normal)."""
        health_paths = ['/health', '/ping', '/status', '/metrics']
        return any(path.startswith(hp) for hp in health_paths)

    def is_static_resource(self, path: str) -> bool:
        """Verifica se é um recurso estático."""
        static_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2']
        return any(path.endswith(ext) for ext in static_extensions) or path.startswith('/static/')

    def analyze_request_pattern(self, request: Request, client_ip: str, response_time: float) -> Dict:
        """Analisa padrões de requisição para detectar anomalias."""
        current_time = time.time()
        ip_data = self.suspicious_ips[client_ip]

        ip_data['requests'] += 1
        ip_data['last_request'] = current_time

        # Exceção para endpoints de desenvolvimento/monitoramento
        allowed_paths = ['/api/v1/infracoes/explorador', '/explorador', '/api/docs', '/metrics']
        is_allowed_path = any(request.url.path.startswith(path) for path in allowed_paths)

        # Exceção para localhost durante desenvolvimento
        is_localhost = client_ip in ['127.0.0.1', 'localhost', '::1']

        # Detectar padrões suspeitos
        anomalies = []

        # Requisições muito rápidas em sequência (possível bot) - MAS não para localhost durante desenvolvimento
        if not (is_allowed_path and is_localhost):
            if response_time < 0.01 and ip_data['requests'] > 50:  # Aumentado de 10 para 50
                anomalies.append('very_fast_requests')

        # User agent suspeito - MAS não para endpoints permitidos ou localhost
        if not (is_allowed_path and is_localhost):
            user_agent = request.headers.get('user-agent', '').lower()
            suspicious_agents = ['curl', 'wget', 'python', 'bot', 'scanner', 'crawler']
            if any(agent in user_agent for agent in suspicious_agents):
                anomalies.append('suspicious_user_agent')

        # Falta de headers comuns - MAS não para endpoints permitidos ou localhost
        if not (is_allowed_path and is_localhost):
            if not request.headers.get('accept') or not request.headers.get('accept-language'):
                anomalies.append('missing_common_headers')

        # Muitos erros do mesmo IP
        if ip_data['errors'] > 5:
            anomalies.append('high_error_rate')

        return {
            'ip': client_ip,
            'anomalies': anomalies,
            'request_count': ip_data['requests'],
            'error_count': ip_data['errors']
        }

    def update_metrics(self, method: str, path: str, status_code: int, response_time: float):
        """Atualiza métricas da aplicação."""
        # Contadores globais
        self.request_count += 1
        self.response_times.append(response_time)
        self.status_codes[status_code] += 1

        if status_code >= 400:
            self.error_count += 1

        # Métricas por endpoint
        endpoint_key = f"{method} {path}"
        stats = self.endpoint_stats[endpoint_key]

        stats['count'] += 1
        stats['total_time'] += response_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['min_time'] = min(stats['min_time'], response_time)
        stats['max_time'] = max(stats['max_time'], response_time)

        if status_code >= 400:
            stats['error_count'] += 1

    async def dispatch(self, request: Request, call_next):
        """Processa a requisição com monitoramento completo."""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        client_ip = self.get_client_ip(request)

        # Adicionar request ID ao contexto
        request.state.request_id = request_id

        try:
            # Processar requisição
            response = await call_next(request)

            # Calcular tempo de resposta
            response_time = time.time() - start_time
            status_code = response.status_code

            # Adicionar headers de monitoramento
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{response_time:.3f}"

            # Pular logging para recursos estáticos e health checks
            if not self.is_static_resource(request.url.path) and not self.is_health_check(request.url.path):

                # Log de acesso
                log_api_access(
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    response_time=response_time,
                    user_ip=client_ip,
                    user_agent=request.headers.get('user-agent')
                )

                # Atualizar métricas
                self.update_metrics(request.method, request.url.path, status_code, response_time)

                # Analisar padrões suspeitos
                if status_code >= 400:
                    self.suspicious_ips[client_ip]['errors'] += 1

                pattern_analysis = self.analyze_request_pattern(request, client_ip, response_time)

                if pattern_analysis['anomalies']:
                    log_security_event(
                        event_type='suspicious_request_pattern',
                        details={
                            'ip': client_ip,
                            'path': request.url.path,
                            'method': request.method,
                            'anomalies': pattern_analysis['anomalies'],
                            'user_agent': request.headers.get('user-agent'),
                            'request_count': pattern_analysis['request_count']
                        },
                        severity='WARNING'
                    )

                # Log de performance para operações lentas
                if response_time > 1.0:
                    log_performance(
                        operation=f"{request.method} {request.url.path}",
                        execution_time=response_time,
                        details={
                            'status_code': status_code,
                            'client_ip': client_ip,
                            'request_id': request_id
                        }
                    )

            return response

        except Exception as e:
            # Log de erro
            response_time = time.time() - start_time
            self.error_count += 1
            self.suspicious_ips[client_ip]['errors'] += 1

            # Log do erro
            self.logger.error(f"Unhandled error in request {request_id}: {str(e)}", extra={
                'request_id': request_id,
                'client_ip': client_ip,
                'method': request.method,
                'path': request.url.path,
                'response_time': response_time,
                'error_type': type(e).__name__
            })

            # Log de segurança para muitos erros
            if self.suspicious_ips[client_ip]['errors'] > 10:
                log_security_event(
                    event_type='high_error_rate',
                    details={
                        'ip': client_ip,
                        'error_count': self.suspicious_ips[client_ip]['errors'],
                        'path': request.url.path,
                        'latest_error': str(e)
                    },
                    severity='ERROR'
                )

            # Re-raise para permitir handling upstream
            raise

    def get_metrics(self) -> Dict:
        """Retorna métricas da aplicação."""
        # Calcular métricas de response time
        if self.response_times:
            sorted_times = sorted(self.response_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            avg_time = sum(self.response_times) / len(self.response_times)
        else:
            p50 = p95 = p99 = avg_time = 0

        # Top endpoints por volume
        top_endpoints = sorted(
            [(k, v['count']) for k, v in self.endpoint_stats.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Endpoints mais lentos
        slow_endpoints = sorted(
            [(k, v['avg_time']) for k, v in self.endpoint_stats.items() if v['count'] > 1],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': (self.error_count / max(self.request_count, 1)) * 100,
            'response_times': {
                'avg': avg_time,
                'p50': p50,
                'p95': p95,
                'p99': p99
            },
            'status_codes': dict(self.status_codes),
            'top_endpoints': top_endpoints,
            'slow_endpoints': slow_endpoints,
            'suspicious_ips_count': len([ip for ip, data in self.suspicious_ips.items()
                                       if data['errors'] > 3 or data['requests'] > 100])
        }

    def reset_metrics(self):
        """Reset das métricas (útil para testes ou limpeza periódica)."""
        self.request_count = 0
        self.error_count = 0
        self.response_times.clear()
        self.endpoint_stats.clear()
        self.status_codes.clear()
        # Manter dados de IPs suspeitos por segurança

    def cleanup_old_data(self):
        """Limpa dados antigos para economizar memória."""
        current_time = time.time()

        # Remover IPs que não fazem requisições há mais de 1 hora
        old_ips = [
            ip for ip, data in self.suspicious_ips.items()
            if current_time - data['last_request'] > 3600
        ]

        for ip in old_ips:
            del self.suspicious_ips[ip]

        # Limitar response_times a 1000 entradas (já feito pelo deque)
        # Limitar endpoint_stats a 500 endpoints
        if len(self.endpoint_stats) > 500:
            # Manter apenas os endpoints mais ativos
            sorted_endpoints = sorted(
                self.endpoint_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )

            self.endpoint_stats.clear()
            for endpoint, stats in sorted_endpoints[:500]:
                self.endpoint_stats[endpoint] = stats