"""
Middleware de segurança para proteção contra ataques e rate limiting.
"""
import time
import hashlib
from typing import Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import re
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware de segurança com rate limiting, proteção contra bots e validação de headers.
    """

    def __init__(
        self,
        app: ASGIApp,
        rate_limit_requests: int = 100,  # Requests por minuto
        rate_limit_window: int = 60,     # Janela em segundos
        block_duration: int = 300,       # Tempo de bloqueio em segundos (5 min)
        max_request_size: int = 1024 * 1024,  # 1MB
        enable_bot_protection: bool = True
    ):
        super().__init__(app)
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self.block_duration = block_duration
        self.max_request_size = max_request_size
        self.enable_bot_protection = enable_bot_protection

        # Armazenamento em memória para rate limiting
        self.client_requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_clients: Dict[str, float] = {}
        self.suspicious_ips: Dict[str, int] = defaultdict(int)

        # Padrões de ataques comuns
        self.attack_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'<script.*?>',
            r'javascript:',
            r'onload\s*=',
            r'onclick\s*=',
            r'eval\s*\(',
            r'document\.cookie',
            r'\.\.\/.*\.\./',
            r'\/etc\/passwd',
            r'cmd\.exe',
            r'powershell',
            r'wget\s+',
            r'curl\s+',
        ]

        # User agents suspeitos
        self.suspicious_user_agents = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap', 'burp',
            'scanner', 'crawler', 'spider', 'bot', 'curl', 'wget',
            'python-requests', 'python-urllib', 'php', 'perl'
        ]

        # Compile patterns para performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.attack_patterns]

    def get_client_ip(self, request: Request) -> str:
        """Obtém o IP real do cliente considerando proxies."""
        # Verificar headers de proxy em ordem de prioridade
        forwarded_ips = request.headers.get("x-forwarded-for")
        if forwarded_ips:
            # Pegar o primeiro IP (cliente original)
            return forwarded_ips.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"

    def is_bot_request(self, request: Request) -> bool:
        """Detecta se a requisição parece ser de um bot malicioso."""
        if not self.enable_bot_protection:
            return False

        user_agent = request.headers.get("user-agent", "").lower()

        # Verificar user agents suspeitos
        for suspicious_ua in self.suspicious_user_agents:
            if suspicious_ua in user_agent:
                return True

        # Verificar se não tem user agent (muito suspeito)
        if not user_agent or len(user_agent) < 10:
            return True

        # Verificar headers suspeitos
        if not request.headers.get("accept"):
            return True

        return False

    def has_attack_patterns(self, content: str) -> bool:
        """Verifica se o conteúdo contém padrões de ataque."""
        if not content:
            return False

        content_lower = content.lower()

        for pattern in self.compiled_patterns:
            if pattern.search(content_lower):
                return True

        return False

    def is_rate_limited(self, client_ip: str) -> bool:
        """Verifica se o cliente excedeu o rate limit."""
        current_time = time.time()

        # Exceção para localhost durante desenvolvimento
        if client_ip in ['127.0.0.1', 'localhost', '::1']:
            return False

        # Verificar se está bloqueado
        if client_ip in self.blocked_clients:
            if current_time - self.blocked_clients[client_ip] < self.block_duration:
                return True
            else:
                # Remover do bloqueio após expirar
                del self.blocked_clients[client_ip]
                # Reset contador de requisições
                self.client_requests[client_ip].clear()

        # Limpar requisições antigas
        client_queue = self.client_requests[client_ip]
        while client_queue and current_time - client_queue[0] > self.rate_limit_window:
            client_queue.popleft()

        # Verificar rate limit
        if len(client_queue) >= self.rate_limit_requests:
            # Bloquear cliente
            self.blocked_clients[client_ip] = current_time
            self.suspicious_ips[client_ip] += 1
            logger.warning(f"Rate limit exceeded for IP {client_ip}. Blocked for {self.block_duration}s")
            return True

        # Adicionar requisição atual
        client_queue.append(current_time)
        return False

    def validate_request_size(self, request: Request) -> bool:
        """Valida o tamanho da requisição."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            return False
        return True

    async def dispatch(self, request: Request, call_next):
        """Processa a requisição aplicando todas as validações de segurança."""
        client_ip = self.get_client_ip(request)

        try:
            # 1. Validar tamanho da requisição
            if not self.validate_request_size(request):
                logger.warning(f"Request too large from IP {client_ip}")
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request entity too large"}
                )

            # 2. Verificar rate limiting
            if self.is_rate_limited(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many requests. Try again later.",
                        "retry_after": self.block_duration
                    },
                    headers={"Retry-After": str(self.block_duration)}
                )

            # 3. Detectar bots maliciosos
            if self.is_bot_request(request):
                self.suspicious_ips[client_ip] += 1
                logger.warning(f"Suspicious bot detected from IP {client_ip}")

                # Se muito suspeito, bloquear
                if self.suspicious_ips[client_ip] > 3:
                    self.blocked_clients[client_ip] = time.time()
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Access denied"}
                    )

            # 4. Verificar padrões de ataque na URL
            url_path = str(request.url.path)
            query_params = str(request.url.query) if request.url.query else ""

            if self.has_attack_patterns(url_path) or self.has_attack_patterns(query_params):
                self.suspicious_ips[client_ip] += 5  # Penalidade maior
                logger.warning(f"Attack pattern detected in URL from IP {client_ip}: {url_path}")
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request"}
                )

            # 5. Para requisições POST/PUT, verificar body
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    if self.has_attack_patterns(body_str):
                        self.suspicious_ips[client_ip] += 5
                        logger.warning(f"Attack pattern detected in body from IP {client_ip}")
                        return JSONResponse(
                            status_code=400,
                            content={"detail": "Invalid request data"}
                        )

                # Recriar request com body para próximo middleware
                request._body = body

            # Processar requisição
            response = await call_next(request)

            # Adicionar headers de segurança
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

            # Não adicionar server header
            if "server" in response.headers:
                del response.headers["server"]

            return response

        except Exception as e:
            logger.error(f"Security middleware error for IP {client_ip}: {str(e)}")
            # Em caso de erro, permitir a requisição mas logar
            response = await call_next(request)
            return response

    def cleanup_old_data(self):
        """Limpa dados antigos para economizar memória."""
        current_time = time.time()

        # Limpar bloqueios expirados
        expired_blocks = [
            ip for ip, block_time in self.blocked_clients.items()
            if current_time - block_time > self.block_duration
        ]
        for ip in expired_blocks:
            del self.blocked_clients[ip]

        # Limpar requisições antigas
        for ip, queue in list(self.client_requests.items()):
            while queue and current_time - queue[0] > self.rate_limit_window:
                queue.popleft()
            if not queue:
                del self.client_requests[ip]

        # Reduzir contadores de IPs suspeitos
        for ip in list(self.suspicious_ips.keys()):
            self.suspicious_ips[ip] = max(0, self.suspicious_ips[ip] - 1)
            if self.suspicious_ips[ip] == 0:
                del self.suspicious_ips[ip]

    def get_security_stats(self) -> Dict:
        """Retorna estatísticas de segurança."""
        current_time = time.time()

        active_blocks = sum(
            1 for block_time in self.blocked_clients.values()
            if current_time - block_time < self.block_duration
        )

        return {
            "active_clients": len(self.client_requests),
            "blocked_clients": active_blocks,
            "suspicious_ips": len(self.suspicious_ips),
            "total_blocks": len(self.blocked_clients)
        }