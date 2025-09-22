"""
Sistema de Correção Ortográfica Leve para MultasGO
Substitui RapidFuzz por soluções nativas Python estáveis e performantes.

Estratégia em camadas:
1. Busca exata
2. Dicionário de correções comuns em português
3. Normalização (acentos, case)
4. Similaridade com difflib (Python nativo)
5. Levenshtein simples para casos extremos
"""
import difflib
import re
import unicodedata
import time
from typing import List, Dict, Tuple, Optional, Set
from functools import lru_cache

from app.core.logger import logger
from app.core.cache_manager import smart_cache


class SpellCorrector:
    """
    Corretor ortográfico otimizado para termos de trânsito em português.

    Features:
    - Correções comuns pré-definidas
    - Normalização automática
    - Busca aproximada nativa
    - Cache inteligente
    - Performance otimizada
    """

    def __init__(self):
        # Dicionário de correções comuns em português (trânsito)
        self.correcoes_comuns = {
            # Erros comuns com película/insulfilm
            "peliculla": "pelicula",
            "pelliculas": "peliculas",
            "pelicula": "pelicula",
            "insufilm": "insulfilm",
            "insulfilme": "insulfilm",
            "insulfime": "insulfilm",
            "insufilme": "insulfilm",

            # Erros de trânsito
            "tansito": "transito",
            "trasito": "transito",
            "transitto": "transito",
            "transsito": "transito",

            # Infrações comuns
            "infraçao": "infracao",
            "infracão": "infracao",
            "infrasao": "infracao",
            "infracao": "infracao",

            # Velocidade
            "velosidade": "velocidade",
            "velocidade": "velocidade",
            "velicidade": "velocidade",
            "belocidade": "velocidade",

            # Álcool
            "alcol": "alcool",
            "alcool": "alcool",
            "alchool": "alcool",
            "alkool": "alcool",
            "alcohol": "alcool",

            # Celular
            "selular": "celular",
            "cellular": "celular",
            "cellar": "celular",
            "telefone": "celular",
            "telefon": "celular",

            # Direção
            "direcao": "direcao",
            "diresao": "direcao",
            "direcção": "direcao",

            # Estacionamento
            "estacionamento": "estacionar",
            "estacionar": "estacionar",
            "estacioanr": "estacionar",
            "estacionar": "estacionar",
            "parar": "estacionar",

            # Veículo
            "veiculo": "veiculo",
            "vehiculo": "veiculo",
            "veiculo": "veiculo",
            "automovel": "veiculo",
            "carro": "veiculo",

            # Farol/sinal
            "faroll": "farol",
            "pharol": "farol",
            "sinal": "farol",
            "sinalizacao": "sinalizacao",
            "sinalização": "sinalizacao",

            # Documentação
            "documentos": "documento",
            "documento": "documento",
            "documneto": "documento",
            "documetno": "documento",

            # Habilitação
            "habilitaçao": "habilitacao",
            "habilitacao": "habilitacao",
            "carteira": "habilitacao",
            "cnh": "habilitacao",

            # Capacete
            "capacete": "capacete",
            "casacete": "capacete",
            "capacette": "capacete",

            # Conversão/circulação
            "conversao": "conversao",
            "circulacao": "circulacao",
            "circulaçao": "circulacao",

            # Local/estrada
            "estrada": "via",
            "rua": "via",
            "avenida": "via",
            "rodovia": "via",

            # Motocicleta
            "motocicleta": "motocicleta",
            "motocileta": "motocicleta",
            "moto": "motocicleta",
            "motoca": "motocicleta",
            "bike": "motocicleta",

            # Condutor
            "condutor": "condutor",
            "conditor": "condutor",
            "motorista": "condutor",
            "piloto": "condutor",

            # Passageiro
            "passageiro": "passageiro",
            "pasageiro": "passageiro",
            "pasajeiro": "passageiro",

            # Cinturão
            "cinto": "cinto",
            "cinturao": "cinto",
            "cinturo": "cinto",
            "cinturão": "cinto",

            # Placa
            "placa": "placa",
            "placas": "placa",
            "plaka": "placa",

            # Segurança
            "seguranca": "seguranca",
            "segurança": "seguranca",
            "segurnaca": "seguranca",

            # Ultrapassagem
            "ultrapassagem": "ultrapassagem",
            "ultrapassar": "ultrapassagem",
            "ultrpassagem": "ultrapassagem",

            # Retorno
            "retorno": "retorno",
            "retornar": "retorno",
            "retrno": "retorno",

            # Estacionar em local proibido
            "proibido": "proibido",
            "proibida": "proibido",
            "probido": "proibido",
            "poibido": "proibido"
        }

        # Termos técnicos com frequência alta
        self.termos_prioritarios = {
            "velocidade", "alcool", "celular", "farol", "estacionar",
            "veiculo", "documento", "habilitacao", "capacete", "conversao",
            "pelicula", "insulfilm", "transito", "infracao", "condutor",
            "motocicleta", "passageiro", "cinto", "placa", "seguranca",
            "ultrapassagem", "retorno", "proibido", "sinalizacao"
        }

        # Estatísticas de uso
        self.stats = {
            "total_corrections": 0,
            "exact_matches": 0,
            "dictionary_corrections": 0,
            "similarity_corrections": 0,
            "no_corrections": 0,
            "avg_correction_time": 0
        }

        logger.info(f"SpellCorrector inicializado com {len(self.correcoes_comuns)} correções")

    @smart_cache(cache_name="search", ttl=600)  # Cache por 10 minutos
    def corrigir_termo(self, termo: str, palavras_banco: List[str],
                      limite_similaridade: float = 0.6) -> Tuple[str, float, str]:
        """
        Corrige termo usando estratégia em camadas.

        Returns:
            Tuple[termo_corrigido, confiança, método_usado]
        """
        start_time = time.time()
        termo_original = termo

        try:
            # Normalizar entrada
            termo = self._normalizar_texto(termo)

            if not termo or len(termo) < 2:
                return termo_original, 0.0, "invalid"

            # 1. BUSCA EXATA (mais rápida)
            if termo in palavras_banco:
                self._update_stats("exact_matches", start_time)
                return termo, 1.0, "exact"

            # 2. DICIONÁRIO DE CORREÇÕES COMUNS
            if termo.lower() in self.correcoes_comuns:
                termo_corrigido = self.correcoes_comuns[termo.lower()]
                if termo_corrigido in palavras_banco:
                    self._update_stats("dictionary_corrections", start_time)
                    return termo_corrigido, 0.95, "dictionary"

            # 3. NORMALIZAÇÃO + BUSCA
            termo_normalizado = self._remover_acentos(termo)
            palavras_normalizadas = [self._remover_acentos(p) for p in palavras_banco]

            if termo_normalizado in palavras_normalizadas:
                idx = palavras_normalizadas.index(termo_normalizado)
                self._update_stats("similarity_corrections", start_time)
                return palavras_banco[idx], 0.9, "normalized"

            # 4. SIMILARIDADE COM DIFFLIB (nativo Python)
            termo_corrigido = self._busca_similaridade_difflib(
                termo_normalizado, palavras_banco, limite_similaridade
            )

            if termo_corrigido:
                self._update_stats("similarity_corrections", start_time)
                return termo_corrigido, 0.8, "similarity"

            # 5. LEVENSHTEIN SIMPLES (último recurso)
            if len(termo) <= 15:  # Só para termos não muito longos
                termo_corrigido = self._levenshtein_correction(
                    termo, palavras_banco, max_distance=2
                )

                if termo_corrigido:
                    self._update_stats("similarity_corrections", start_time)
                    return termo_corrigido, 0.7, "levenshtein"

            # Sem correção encontrada
            self._update_stats("no_corrections", start_time)
            return termo_original, 0.0, "none"

        except Exception as e:
            logger.warning(f"Erro na correção de '{termo_original}': {e}")
            return termo_original, 0.0, "error"

    def _normalizar_texto(self, texto: str) -> str:
        """Normalização básica do texto."""
        if not isinstance(texto, str):
            return ""

        # Converter para minúsculo e remover espaços extras
        texto = texto.lower().strip()

        # Remover caracteres especiais mas manter acentos
        texto = re.sub(r'[^\w\sáàâãéèêíìîóòôõúùûç]', '', texto)

        # Remover espaços múltiplos
        texto = re.sub(r'\s+', ' ', texto)

        return texto

    def _remover_acentos(self, texto: str) -> str:
        """Remove acentos mantendo caracteres básicos."""
        if not texto:
            return ""

        # Normalização Unicode para remover acentos
        texto_nfd = unicodedata.normalize('NFD', texto)
        texto_sem_acentos = ''.join(c for c in texto_nfd if unicodedata.category(c) != 'Mn')

        return texto_sem_acentos

    def _busca_similaridade_difflib(self, termo: str, palavras: List[str],
                                   limite: float = 0.6) -> Optional[str]:
        """Busca por similaridade usando difflib (Python nativo)."""
        try:
            # Usar difflib.get_close_matches para busca eficiente
            matches = difflib.get_close_matches(
                termo,
                palavras,
                n=1,  # Apenas o melhor match
                cutoff=limite
            )

            if matches:
                return matches[0]

            # Busca mais específica para termos prioritários
            if len(termo) >= 4:
                for palavra_prioritaria in self.termos_prioritarios:
                    if palavra_prioritaria in palavras:
                        similaridade = difflib.SequenceMatcher(
                            None, termo, palavra_prioritaria
                        ).ratio()

                        if similaridade >= limite:
                            return palavra_prioritaria

            return None

        except Exception as e:
            logger.debug(f"Erro na busca difflib: {e}")
            return None

    def _levenshtein_correction(self, termo: str, palavras: List[str],
                               max_distance: int = 2) -> Optional[str]:
        """Correção usando distância de Levenshtein simples."""
        try:
            melhor_palavra = None
            menor_distancia = max_distance + 1

            # Limitar a busca para performance
            palavras_candidatas = [p for p in palavras if abs(len(p) - len(termo)) <= max_distance]

            for palavra in palavras_candidatas[:50]:  # Máximo 50 comparações
                distancia = self._levenshtein_distance(termo, palavra)

                if distancia <= max_distance and distancia < menor_distancia:
                    menor_distancia = distancia
                    melhor_palavra = palavra

                    # Se encontrou distância 1, é muito boa
                    if distancia == 1:
                        break

            return melhor_palavra

        except Exception as e:
            logger.debug(f"Erro no Levenshtein: {e}")
            return None

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Implementação simples da distância de Levenshtein."""
        if len(s1) < len(s2):
            return SpellCorrector._levenshtein_distance(s2, s1)

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

    def _update_stats(self, tipo: str, start_time: float):
        """Atualiza estatísticas de uso."""
        self.stats["total_corrections"] += 1
        self.stats[tipo] += 1

        correction_time = time.time() - start_time
        total = self.stats["total_corrections"]
        self.stats["avg_correction_time"] = (
            (self.stats["avg_correction_time"] * (total - 1) + correction_time) / total
        )

    def get_stats(self) -> Dict:
        """Retorna estatísticas de uso do corretor."""
        total = self.stats["total_corrections"]
        if total == 0:
            return self.stats

        return {
            **self.stats,
            "success_rate": round(
                (total - self.stats["no_corrections"]) / total * 100, 2
            ),
            "avg_correction_time_ms": round(
                self.stats["avg_correction_time"] * 1000, 2
            ),
            "dictionary_rate": round(
                self.stats["dictionary_corrections"] / total * 100, 2
            )
        }

    def adicionar_correcao(self, termo_erro: str, termo_correto: str):
        """Adiciona nova correção ao dicionário."""
        self.correcoes_comuns[termo_erro.lower()] = termo_correto.lower()
        logger.info(f"Correção adicionada: '{termo_erro}' -> '{termo_correto}'")

    def buscar_sugestoes(self, termo: str, palavras_banco: List[str],
                        max_sugestoes: int = 5) -> List[Tuple[str, float]]:
        """
        Retorna múltiplas sugestões de correção com scores.

        Returns:
            List[Tuple[palavra_sugerida, confiança]]
        """
        try:
            termo_normalizado = self._normalizar_texto(termo)
            sugestoes = []

            # Usar difflib para encontrar matches múltiplos
            matches = difflib.get_close_matches(
                termo_normalizado,
                palavras_banco,
                n=max_sugestoes,
                cutoff=0.5
            )

            for match in matches:
                # Calcular score de confiança
                score = difflib.SequenceMatcher(None, termo_normalizado, match).ratio()
                sugestoes.append((match, round(score, 3)))

            # Ordenar por score
            sugestoes.sort(key=lambda x: x[1], reverse=True)

            return sugestoes[:max_sugestoes]

        except Exception as e:
            logger.warning(f"Erro ao buscar sugestões para '{termo}': {e}")
            return []

    def benchmark_performance(self, termos_teste: List[str],
                            palavras_banco: List[str]) -> Dict:
        """Testa performance do corretor com lista de termos."""
        start_time = time.time()
        resultados = []

        for termo in termos_teste:
            termo_corrigido, confianca, metodo = self.corrigir_termo(termo, palavras_banco)
            resultados.append({
                "original": termo,
                "corrigido": termo_corrigido,
                "confianca": confianca,
                "metodo": metodo
            })

        total_time = time.time() - start_time

        return {
            "total_termos": len(termos_teste),
            "tempo_total_s": round(total_time, 3),
            "tempo_medio_ms": round((total_time / len(termos_teste)) * 1000, 2),
            "resultados": resultados,
            "stats": self.get_stats()
        }


# Instância global do corretor
spell_corrector = SpellCorrector()


# Função de conveniência para usar no search_service
def corrigir_termo_busca(termo: str, palavras_banco: List[str]) -> Tuple[str, float]:
    """
    Função simplificada para integração com search_service.

    Returns:
        Tuple[termo_corrigido, confiança]
    """
    termo_corrigido, confianca, _ = spell_corrector.corrigir_termo(termo, palavras_banco)
    return termo_corrigido, confianca


# Função de teste para validar correções
def testar_correcoes_comuns():
    """Testa correções comuns para validar o funcionamento."""
    termos_teste = [
        "peliculla", "tansito", "infraçao", "velosidade", "alcol",
        "selular", "estacionamento", "veiculo", "faroll", "documentos",
        "habilitaçao", "motocileta", "conditor", "cinturao", "plaka"
    ]

    palavras_banco = [
        "pelicula", "transito", "infracao", "velocidade", "alcool",
        "celular", "estacionar", "veiculo", "farol", "documento",
        "habilitacao", "motocicleta", "condutor", "cinto", "placa"
    ]

    print("=== TESTE DE CORREÇÕES ===")
    for termo in termos_teste:
        corrigido, confianca, metodo = spell_corrector.corrigir_termo(termo, palavras_banco)
        print(f"'{termo}' → '{corrigido}' (confiança: {confianca:.2f}, método: {metodo})")

    print(f"\nEstatísticas: {spell_corrector.get_stats()}")


if __name__ == "__main__":
    testar_correcoes_comuns()