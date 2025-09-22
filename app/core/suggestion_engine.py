"""
Sistema de Sugestões "Você quis dizer..." para MultasGO
Implementa correção ortográfica inteligente sem interferir na busca principal.
"""
import re
from typing import Optional, List, Set
from unidecode import unidecode

from app.core.logger import logger


class SuggestionEngine:
    """
    Engine de sugestões ortográficas estilo Google.

    Estratégias (em ordem de prioridade):
    1. Dicionário de correções diretas (mais rápido)
    2. Distância de Levenshtein com palavras do banco
    3. Correções de acentuação básica
    """

    def __init__(self):
        self.correcoes_diretas = self._criar_dicionario_correcoes()
        self.palavras_banco = set()  # Será populado com palavras do banco

        logger.info(f"SuggestionEngine inicializado com {len(self.correcoes_diretas)} correções diretas")

    def _criar_dicionario_correcoes(self) -> dict:
        """
        Dicionário das 30 correções mais comuns baseadas em logs reais.
        Mistura termos de trânsito + português geral.
        """
        return {
            # === TERMOS DE TRÂNSITO MAIS COMUNS ===
            "velocidde": "velocidade",
            "velosidade": "velocidade",
            "velicidade": "velocidade",
            "belocidade": "velocidade",

            "alcol": "alcool",
            "alchool": "alcool",
            "alkool": "alcool",
            "alcohol": "alcool",

            "selular": "celular",
            "cellular": "celular",
            "cellar": "celular",
            "selelar": "celular",

            "tansito": "transito",
            "trasito": "transito",
            "transitto": "transito",
            "transsito": "transito",

            "peliculla": "pelicula",
            "pelliculas": "pelicula",
            "peliculas": "pelicula",

            "insufilm": "insulfilm",
            "insulfilme": "insulfilm",
            "insulfime": "insulfilm",
            "insufilme": "insulfilm",

            "motocileta": "motocicleta",
            "motoca": "motocicleta",
            "moto": "motocicleta",

            "estacionamento": "estacionar",
            "estacioanr": "estacionar",

            "faroll": "farol",
            "pharol": "farol",

            "capacette": "capacete",
            "casacete": "capacete",

            # === ACENTUAÇÃO BÁSICA PORTUGUESA ===
            "infracao": "infracao",  # Já normalizado no sistema
            "infraçao": "infracao",
            "infracão": "infracao",
            "infrasao": "infracao",

            "habilitacao": "habilitacao",
            "habilitaçao": "habilitacao",

            "conversao": "conversacao",
            "conversão": "conversacao",

            "circulacao": "circulacao",
            "circulaçao": "circulacao",

            # === ERROS DE PORTUGUÊS GERAL ===
            "disponivel": "disponivel",  # Já sem acento no sistema
            "acessivel": "acessivel",
            "possivel": "possivel",
            "responsavel": "responsavel",

            "obrigatorio": "obrigatorio",
            "necessario": "necessario",

            "veiculo": "veiculo",
            "vehiculo": "veiculo",
            "automovel": "veiculo",

            # === ERROS DE DIGITAÇÃO COMUNS ===
            "ducumento": "documento",
            "documetno": "documento",
            "documneto": "documento",

            "conditor": "condutor",
            "codnutor": "condutor",

            "pasageiro": "passageiro",
            "pasajeiro": "passageiro",

            "cinturao": "cinto",
            "cinturo": "cinto",
            "sinturao": "cinto",

            "segurnaca": "seguranca",
            "siguranca": "seguranca",

            "ultrpassagem": "ultrapassagem",
            "ultrapassajem": "ultrapassagem",

            "probido": "proibido",
            "poibido": "proibido",
            "probibido": "proibido",
        }

    def atualizar_palavras_banco(self, palavras: Set[str]):
        """
        Atualiza o conjunto de palavras válidas do banco de dados.
        Deve ser chamado quando o cache de palavras for atualizado.
        """
        self.palavras_banco = {unidecode(p.lower()) for p in palavras if p and len(p) >= 3}
        logger.debug(f"Palavras do banco atualizadas: {len(self.palavras_banco)} termos")

    def verificar_ortografia(self, palavra: str) -> Optional[str]:
        """
        Verifica ortografia e retorna sugestão se necessário.

        Args:
            palavra: Palavra digitada pelo usuário

        Returns:
            Sugestão corrigida ou None se a palavra estiver correta
        """
        if not palavra or len(palavra) < 2:
            return None

        palavra_normalizada = unidecode(palavra.lower().strip())

        # Estratégia 1: Correções diretas (mais rápido)
        if palavra_normalizada in self.correcoes_diretas:
            sugestao = self.correcoes_diretas[palavra_normalizada]
            logger.debug(f"Correção direta: '{palavra}' → '{sugestao}'")
            return sugestao

        # Estratégia 2: Verificar se já está correta
        if palavra_normalizada in self.palavras_banco:
            return None  # Palavra está correta

        # Estratégia 3: Levenshtein com palavras do banco
        sugestao_levenshtein = self._buscar_similar_levenshtein(palavra_normalizada)
        if sugestao_levenshtein:
            logger.debug(f"Correção por Levenshtein: '{palavra}' → '{sugestao_levenshtein}'")
            return sugestao_levenshtein

        # Estratégia 4: Correções de acentuação comum
        sugestao_acentos = self._corrigir_acentos_comuns(palavra_normalizada)
        if sugestao_acentos:
            logger.debug(f"Correção de acentos: '{palavra}' → '{sugestao_acentos}'")
            return sugestao_acentos

        return None

    def _buscar_similar_levenshtein(self, palavra: str, max_distancia: int = 2) -> Optional[str]:
        """
        Busca palavra similar usando distância de Levenshtein.
        """
        if not self.palavras_banco:
            return None

        melhor_match = None
        menor_distancia = max_distancia + 1

        # Filtrar candidatos por tamanho similar (otimização)
        candidatos = [p for p in self.palavras_banco
                     if abs(len(p) - len(palavra)) <= max_distancia and len(p) >= 3]

        for candidato in candidatos:
            distancia = self._calcular_levenshtein(palavra, candidato)
            if distancia <= max_distancia and distancia < menor_distancia:
                menor_distancia = distancia
                melhor_match = candidato

        return melhor_match

    def _calcular_levenshtein(self, s1: str, s2: str) -> int:
        """
        Calcula distância de Levenshtein entre duas strings.
        Algoritmo otimizado para strings curtas.
        """
        if len(s1) < len(s2):
            return self._calcular_levenshtein(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _corrigir_acentos_comuns(self, palavra: str) -> Optional[str]:
        """
        Tenta correções básicas de acentuação.
        """
        # Lista de sufixos comuns com/sem acentos
        correcoes_sufixos = [
            ('cao', 'cao'),    # ação → acao
            ('sao', 'sao'),    # são → sao
            ('vel', 'vel'),    # ável → avel
            ('rio', 'rio'),    # ório → orio
        ]

        for sufixo_errado, sufixo_certo in correcoes_sufixos:
            if palavra.endswith(sufixo_errado):
                candidato = palavra[:-len(sufixo_errado)] + sufixo_certo
                if candidato in self.palavras_banco:
                    return candidato

        return None

    def get_stats(self) -> dict:
        """Retorna estatísticas do sistema de sugestões."""
        return {
            "correcoes_diretas": len(self.correcoes_diretas),
            "palavras_banco": len(self.palavras_banco),
            "status": "ativo"
        }


# Instância global
suggestion_engine = SuggestionEngine()