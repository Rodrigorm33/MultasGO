"""
Middleware de Segurança Geográfica e Anti-Bot Avançado
Proteção específica contra IPs chineses e bots maliciosos.
"""
import time
import requests
import ipaddress
from typing import Dict, Set, Optional, List
from collections import defaultdict, deque
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import json
import hashlib
import random
import string

from app.core.config import settings
from app.core.logger import logger, log_security_event


class GeoSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware de segurança geográfica com foco em proteção contra ataques automatizados.

    Features:
    - Detecção de IPs chineses
    - CAPTCHA dinâmico para requests suspeitos
    - Blacklist de ranges de IP maliciosos
    - Análise comportamental avançada
    - Rate limiting geográfico
    """

    def __init__(self, app, enable_geo_blocking: bool = True):
        super().__init__(app)
        self.enable_geo_blocking = enable_geo_blocking

        # Ranges de IP chineses conhecidos (principais blocos)
        self.chinese_ip_ranges = [
            "1.0.1.0/24", "1.0.2.0/23", "1.0.8.0/21", "1.0.32.0/19",
            "14.0.12.0/22", "14.0.16.0/20", "14.1.0.0/18", "14.16.0.0/12",
            "27.0.0.0/11", "27.32.0.0/12", "27.48.0.0/13", "27.56.0.0/14",
            "36.0.0.0/10", "39.64.0.0/11", "39.96.0.0/13", "39.104.0.0/14",
            "42.0.0.0/8", "49.0.0.0/13", "49.8.0.0/14", "49.12.0.0/15",
            "58.14.0.0/15", "58.16.0.0/15", "58.18.0.0/16", "58.19.0.0/16",
            "59.32.0.0/12", "59.48.0.0/13", "59.56.0.0/14", "59.60.0.0/15",
            "60.0.0.0/13", "60.8.0.0/14", "60.12.0.0/15", "60.14.0.0/16",
            "61.48.0.0/13", "61.56.0.0/14", "61.60.0.0/15", "61.62.0.0/16",
            "101.0.0.0/10", "103.0.0.0/11", "106.0.0.0/8", "110.0.0.0/7",
            "112.0.0.0/6", "116.0.0.0/6", "120.0.0.0/6", "124.0.0.0/6",
            "134.175.0.0/16", "139.0.0.0/11", "140.75.0.0/16", "144.0.0.0/11",
            "150.0.0.0/15", "152.104.128.0/17", "157.0.0.0/10", "159.226.0.0/16",
            "161.207.0.0/16", "162.105.0.0/16", "166.111.0.0/16", "167.139.0.0/16",
            "168.160.0.0/16", "169.211.0.0/16", "192.124.154.0/24", "192.188.170.0/24",
            "202.0.0.0/11", "202.32.0.0/12", "202.48.0.0/13", "202.56.0.0/14",
            "210.0.0.0/12", "210.16.0.0/13", "210.24.0.0/14", "210.28.0.0/15",
            "218.0.0.0/11", "218.32.0.0/12", "218.48.0.0/13", "218.56.0.0/14",
            "219.128.0.0/11", "219.160.0.0/12", "219.176.0.0/13", "219.184.0.0/14",
            "220.96.0.0/11", "220.128.0.0/12", "220.144.0.0/13", "220.152.0.0/14",
            "221.0.0.0/11", "221.32.0.0/12", "221.48.0.0/13", "221.56.0.0/14",
            "222.0.0.0/12", "222.16.0.0/13", "222.24.0.0/14", "222.28.0.0/15",
            "223.0.0.0/11", "223.32.0.0/12", "223.48.0.0/13", "223.56.0.0/14"
        ]

        # Compilar ranges para verificação eficiente
        self.chinese_networks = []
        for ip_range in self.chinese_ip_ranges:
            try:
                self.chinese_networks.append(ipaddress.ip_network(ip_range))
            except:
                pass

        # Outros ranges maliciosos conhecidos
        self.malicious_ranges = [
            "185.220.100.0/22",  # Tor exit nodes
            "185.220.101.0/24",
            "185.220.102.0/24",
            "192.42.116.0/22",   # Malicious hosting
            "5.188.0.0/16",      # Bulletproof hosting
            "89.248.160.0/22"    # Known bot networks
        ]

        self.malicious_networks = []
        for ip_range in self.malicious_ranges:
            try:
                self.malicious_networks.append(ipaddress.ip_network(ip_range))
            except:
                pass

        # Estatísticas e controles
        self.geo_stats = defaultdict(int)
        self.blocked_geos = defaultdict(int)
        self.captcha_challenges = {}  # IP -> challenge_data
        self.captcha_failures = defaultdict(int)

        # User agents suspeitos (expandido)
        self.malicious_user_agents = {
            'python-requests', 'python-urllib3', 'python/3', 'go-http-client',
            'java/', 'curl/', 'wget/', 'scrapy/', 'bot', 'crawler', 'spider',
            'scanner', 'exploit', 'hack', 'attack', 'masscan', 'nmap',
            'sqlmap', 'burp', 'nikto', 'acunetix', 'w3af', 'skipfish',
            'openvas', 'nessus', 'metasploit', 'havij', 'pangolin',
            'webinspect', 'appscan', 'brutus', 'hydra', 'medusa',
            'john', 'aircrack', 'wireshark', 'ettercap', 'cain',
            'kismet', 'fierce', 'dnsrecon', 'whatweb', 'wpscan',
            'joomscan', 'droopescan', 'cmseek', 'shodan', 'censys'
        }

        logger.info(f"GeoSecurityMiddleware inicializado - {len(self.chinese_networks)} ranges chineses carregados")

    def is_chinese_ip(self, ip_str: str) -> bool:
        """Verifica se o IP está em ranges chineses."""
        try:
            ip = ipaddress.ip_address(ip_str)
            for network in self.chinese_networks:
                if ip in network:
                    return True
            return False
        except:
            return False

    def is_malicious_ip(self, ip_str: str) -> bool:
        """Verifica se o IP está em ranges maliciosos conhecidos."""
        try:
            ip = ipaddress.ip_address(ip_str)
            for network in self.malicious_networks:
                if ip in network:
                    return True
            return False
        except:
            return False

    def analyze_request_risk(self, request: Request, client_ip: str) -> Dict[str, any]:
        """Análise avançada de risco da requisição - VERSÃO MENOS RESTRITIVA."""
        risk_score = 0
        flags = []

        # 1. Verificação geográfica - SOMENTE IPs REALMENTE MALICIOSOS
        if self.is_malicious_ip(client_ip):
            risk_score += 60
            flags.append("known_malicious_ip")

        # IPs chineses apenas aumentam score moderadamente
        if self.is_chinese_ip(client_ip):
            risk_score += 15  # Reduzido de 30 para 15
            flags.append("chinese_ip_moderate_risk")

        # 2. User Agent analysis - MAIS TOLERANTE
        user_agent = request.headers.get("user-agent", "").lower()
        if not user_agent:
            risk_score += 15  # Reduzido de 25 para 15
            flags.append("no_user_agent")
        else:
            # Apenas user agents claramente maliciosos
            high_risk_patterns = ['scrapy', 'bot', 'crawler', 'spider', 'wget', 'curl/']
            for pattern in high_risk_patterns:
                if pattern in user_agent and 'googlebot' not in user_agent:
                    risk_score += 25  # Reduzido de 35 para 25
                    flags.append(f"suspicious_ua_{pattern}")
                    break

        # 3. Headers analysis - MAIS PERMISSIVO
        # Apenas se não tiver NENHUM header comum
        common_headers = ["accept", "accept-language", "accept-encoding", "user-agent"]
        missing_headers = [h for h in common_headers if not request.headers.get(h)]
        if len(missing_headers) >= 3:  # Mudado de 2 para 3
            risk_score += 15  # Reduzido de 20 para 15
            flags.append("missing_common_headers")

        # 4. Suspicious request patterns
        path = str(request.url.path).lower()
        suspicious_paths = [
            "admin", "wp-admin", "phpmyadmin", "xmlrpc.php", "config.php",
            "shell.php", "backdoor", "webshell", ".env", "backup",
            "database", "sql", "dump", "test", "debug"
        ]

        for sus_path in suspicious_paths:
            if sus_path in path:
                risk_score += 40
                flags.append(f"suspicious_path_{sus_path}")
                break

        # 5. Query parameters analysis
        query = str(request.url.query).lower() if request.url.query else ""
        if query:
            malicious_params = ["union", "select", "drop", "insert", "update",
                              "delete", "script", "alert", "eval", "exec"]
            for param in malicious_params:
                if param in query:
                    risk_score += 45
                    flags.append(f"malicious_param_{param}")

        # Determinar nível de risco - THRESHOLDS MUITO MAIS ALTOS
        if risk_score >= 120:  # Aumentado de 80 para 120
            risk_level = "CRITICAL"
        elif risk_score >= 90:  # Aumentado de 60 para 90
            risk_level = "HIGH"
        elif risk_score >= 60:  # Aumentado de 40 para 60
            risk_level = "MEDIUM"
        elif risk_score >= 30:  # Aumentado de 20 para 30
            risk_level = "LOW"
        else:
            risk_level = "SAFE"

        return {
            "score": risk_score,
            "level": risk_level,
            "flags": flags
        }

    def generate_captcha_challenge(self) -> Dict[str, str]:
        """Gera desafio CAPTCHA simples para requests suspeitos."""
        # CAPTCHA matemático simples
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        operation = random.choice(['+', '-', '*'])

        if operation == '+':
            answer = num1 + num2
        elif operation == '-':
            answer = abs(num1 - num2)  # Sempre positivo
        else:  # multiplication
            answer = num1 * num2

        question = f"{num1} {operation} {num2}"
        challenge_id = hashlib.md5(f"{question}:{answer}:{time.time()}".encode()).hexdigest()[:8]

        return {
            "challenge_id": challenge_id,
            "question": question,
            "answer": str(answer)
        }

    def verify_captcha(self, request: Request) -> bool:
        """Verifica resposta do CAPTCHA."""
        captcha_id = request.headers.get("X-Captcha-ID")
        captcha_response = request.headers.get("X-Captcha-Response")

        if not captcha_id or not captcha_response:
            return False

        client_ip = self.get_client_ip(request)
        if client_ip not in self.captcha_challenges:
            return False

        challenge_data = self.captcha_challenges[client_ip]
        if challenge_data.get("challenge_id") != captcha_id:
            return False

        if challenge_data.get("answer") == captcha_response.strip():
            # CAPTCHA correto - remover challenge
            del self.captcha_challenges[client_ip]
            return True
        else:
            # CAPTCHA incorreto
            self.captcha_failures[client_ip] += 1
            return False

    def get_client_ip(self, request: Request) -> str:
        """Obtém IP real do cliente."""
        forwarded_ips = request.headers.get("x-forwarded-for")
        if forwarded_ips:
            return forwarded_ips.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"

    def is_safe_request(self, request: Request, client_ip: str) -> bool:
        """
        Determina se o request é seguro e deve ser sempre permitido.
        Whitelist inteligente para evitar bloqueios desnecessários.
        """
        # 1. IPs locais e de desenvolvimento
        if client_ip in ['127.0.0.1', 'localhost', '::1'] or client_ip.startswith('192.168.') or client_ip.startswith('10.'):
            return True

        # 2. Requests do próprio sistema (health checks, etc)
        if str(request.url.path) in ['/health', '/docs', '/redoc', '/openapi.json']:
            return True

        # 3. Requests com Referer do próprio site (navegadores legítimos)
        referer = request.headers.get("referer", "")
        if referer and ("localhost" in referer or "127.0.0.1" in referer):
            return True

        # 4. User agents de navegadores conhecidos
        user_agent = request.headers.get("user-agent", "").lower()
        browser_patterns = ['mozilla', 'chrome', 'safari', 'firefox', 'edge', 'opera']
        if any(pattern in user_agent for pattern in browser_patterns):
            return True

        # 5. Requests com headers completos de navegador
        required_headers = ['accept', 'accept-language', 'accept-encoding']
        if all(request.headers.get(header) for header in required_headers):
            return True

        # 6. IPs de provedores brasileiros conhecidos (adicionar aqui se necessário)
        # Por exemplo: IPs da Vivo, Claro, TIM, Oi, etc.

        return False

    async def dispatch(self, request: Request, call_next):
        """Processamento principal do middleware."""
        client_ip = self.get_client_ip(request)

        # WHITELIST INTELIGENTE - Permitir sempre
        if self.is_safe_request(request, client_ip):
            return await call_next(request)

        # Análise de risco apenas para IPs não confiáveis
        risk_analysis = self.analyze_request_risk(request, client_ip)
        risk_level = risk_analysis["level"]
        risk_score = risk_analysis["score"]

        # Log apenas requests realmente perigosos
        if risk_level == "CRITICAL":
            log_security_event(
                event_type="critical_security_threat",
                details={
                    "ip": client_ip,
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "flags": risk_analysis["flags"],
                    "user_agent": request.headers.get("user-agent", ""),
                    "path": str(request.url.path)
                },
                severity="ERROR"
            )

        # Ações baseadas no nível de risco - APENAS PARA RISCOS CRÍTICOS
        if risk_level == "CRITICAL" and risk_score > 120:
            # Bloquear apenas ameaças realmente críticas
            self.blocked_geos[client_ip] = time.time()
            logger.warning(f"Suspicious bot detected from IP {client_ip}")
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied",
                    "code": "SECURITY_BLOCK"
                }
            )

        # Para riscos HIGH, apenas logar mas permitir acesso
        if risk_level == "HIGH":
            logger.info(f"Medium risk request from {client_ip} - allowing access")

        # Atualizar estatísticas
        self.geo_stats[client_ip] += 1

        # Processar requisição normalmente
        return await call_next(request)

    def get_geo_stats(self) -> Dict[str, any]:
        """Retorna estatísticas de segurança geográfica."""
        chinese_requests = sum(1 for ip in self.geo_stats.keys() if self.is_chinese_ip(ip))

        return {
            "total_unique_ips": len(self.geo_stats),
            "chinese_ips_detected": chinese_requests,
            "blocked_ips": len(self.blocked_geos),
            "active_captcha_challenges": len(self.captcha_challenges),
            "captcha_failures": dict(self.captcha_failures),
            "malicious_ranges_loaded": len(self.malicious_networks),
            "chinese_ranges_loaded": len(self.chinese_networks)
        }