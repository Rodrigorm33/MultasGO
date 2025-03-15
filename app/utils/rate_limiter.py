from time import time
from typing import Dict, Tuple
from fastapi import HTTPException

class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}
    
    def _clean_old_requests(self, ip: str):
        """Remove requisições mais antigas que 1 minuto"""
        now = time()
        self.requests[ip] = [req_time for req_time in self.requests[ip] 
                           if now - req_time < 60]
    
    def check_rate_limit(self, ip: str) -> Tuple[bool, int]:
        """
        Verifica se o IP pode fazer mais requisições
        Retorna: (pode_continuar, tempo_espera)
        """
        now = time()
        
        # Inicializar lista de requisições para o IP se não existir
        if ip not in self.requests:
            self.requests[ip] = []
        
        # Limpar requisições antigas
        self._clean_old_requests(ip)
        
        # Verificar número de requisições no último minuto
        if len(self.requests[ip]) >= self.requests_per_minute:
            oldest_request = self.requests[ip][0]
            wait_time = int(60 - (now - oldest_request))
            return False, wait_time
        
        # Adicionar nova requisição
        self.requests[ip].append(now)
        return True, 0

# Instância global do rate limiter
rate_limiter = RateLimiter() 