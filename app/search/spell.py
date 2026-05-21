"""
Corretor ortográfico unificado para MultasGO.
Merge de spell_corrector.py + suggestion_engine.py.

Estratégia em 5 camadas:
1. Busca exata
2. Dicionário de correções
3. Normalização (acentos, case)
4. Similaridade difflib (Python nativo)
5. Levenshtein simples
"""
import difflib
import re
import unicodedata
import time
from typing import List, Dict, Tuple, Optional, Set

from app.core.logger import logger
from app.search.dictionaries.terms import CORRECOES, TERMOS_PRIORITARIOS


class CorretorOrtografico:
    """Corretor ortográfico unificado para termos de trânsito."""

    def __init__(self):
        self.correcoes = CORRECOES
        self.termos_prioritarios = TERMOS_PRIORITARIOS
        self.palavras_banco: Set[str] = set()
        self.stats = {
            "total_corrections": 0,
            "exact_matches": 0,
            "dictionary_corrections": 0,
            "similarity_corrections": 0,
            "no_corrections": 0,
            "avg_correction_time": 0.0,
        }
        logger.info(f"CorretorOrtografico inicializado com {len(self.correcoes)} correções")

    def atualizar_vocabulario(self, palavras: Set[str]):
        """Atualiza vocabulário com palavras do banco."""
        from unidecode import unidecode
        self.palavras_banco = {unidecode(p.lower()) for p in palavras if p and len(p) >= 3}
        logger.debug(f"Vocabulário atualizado: {len(self.palavras_banco)} termos")

    def corrigir(self, termo: str, palavras_banco: List[str] = None,
                 limite_similaridade: float = 0.6) -> Tuple[str, float, str]:
        """
        Corrige termo em 5 camadas.
        Returns: (termo_corrigido, confiança, método)
        """
        start_time = time.time()
        termo_original = termo

        try:
            termo = self._normalizar(termo)
            if not termo or len(termo) < 2:
                return termo_original, 0.0, "invalid"

            banco = palavras_banco or list(self.palavras_banco)

            # 1. BUSCA EXATA
            if termo in banco:
                self._update_stats("exact_matches", start_time)
                return termo, 1.0, "exact"

            # 2. DICIONÁRIO DE CORREÇÕES
            if termo.lower() in self.correcoes:
                corrigido = self.correcoes[termo.lower()]
                if not banco or corrigido in banco:
                    self._update_stats("dictionary_corrections", start_time)
                    return corrigido, 0.95, "dictionary"

            # 3. NORMALIZAÇÃO + BUSCA
            termo_sem_acento = self._remover_acentos(termo)
            for i, p in enumerate(banco):
                if self._remover_acentos(p) == termo_sem_acento:
                    self._update_stats("similarity_corrections", start_time)
                    return banco[i], 0.9, "normalized"

            # 4. DIFFLIB
            match = self._busca_difflib(termo_sem_acento, banco, limite_similaridade)
            if match:
                self._update_stats("similarity_corrections", start_time)
                return match, 0.8, "similarity"

            # 5. LEVENSHTEIN
            if len(termo) <= 15:
                match = self._levenshtein_correction(termo, banco, max_distance=2)
                if match:
                    self._update_stats("similarity_corrections", start_time)
                    return match, 0.7, "levenshtein"

            self._update_stats("no_corrections", start_time)
            return termo_original, 0.0, "none"

        except Exception as e:
            logger.warning(f"Erro na correção de '{termo_original}': {e}")
            return termo_original, 0.0, "error"

    def sugerir(self, termo: str) -> Optional[str]:
        """Retorna sugestão 'Você quis dizer?' ou None se correto."""
        if not termo or len(termo) < 2:
            return None

        from unidecode import unidecode
        normalizado = unidecode(termo.lower().strip())

        # Correção direta
        if normalizado in self.correcoes:
            return self.correcoes[normalizado]

        # Já correto
        if normalizado in self.palavras_banco:
            return None

        # Se o usuário está digitando um prefixo válido, não sugerir correção aqui.
        # O autocomplete deve cuidar disso; "correção" em prefixos gera ruído.
        if len(normalizado) >= 3:
            try:
                for p in self.palavras_banco:
                    if p.startswith(normalizado):
                        return None
            except Exception:
                pass

        def _common_prefix_len(a: str, b: str) -> int:
            n = 0
            for x, y in zip(a, b):
                if x == y:
                    n += 1
                else:
                    break
            return n

        # Correção por "prefixo fuzzy" (útil quando o usuário ainda está digitando).
        # Ex.: "velc" -> "velocidade" (distância baixa no prefixo "velo").
        if 4 <= len(normalizado) <= 6:
            prior = {unidecode(t.lower().strip()) for t in self.termos_prioritarios}

            melhor = None
            melhor_key = None
            for c in self.palavras_banco:
                if not c:
                    continue
                if len(c) < len(normalizado):
                    continue
                # Reduz o espaço de busca e ruído.
                if c[0] != normalizado[0]:
                    continue
                pref = c[: len(normalizado)]
                dist = self._levenshtein_distance(normalizado, pref)
                if dist > 1:
                    continue
                cpl = _common_prefix_len(normalizado, pref)

                # Confiança mínima: se houve 1 edição, queremos o prefixo praticamente igual.
                if dist == 1 and cpl < max(3, len(normalizado) - 1):
                    continue

                is_prior = 1 if c in prior else 0
                # Ordena por: prefixo mais longo, menor distância, termo prioritário, termo mais completo.
                key = (-cpl, dist, -is_prior, -len(c))
                if melhor_key is None or key < melhor_key:
                    melhor_key = key
                    melhor = c
            if melhor:
                return melhor

        # Levenshtein (conservador): para tokens curtos, a chance de sugerir errado é alta.
        if len(normalizado) < 6:
            return None

        candidatos = [
            p
            for p in self.palavras_banco
            if len(p) >= 3
            and abs(len(p) - len(normalizado)) <= 2
            and p
            and p[0] == normalizado[0]
        ]
        melhor = None
        menor_dist = 3
        for c in candidatos:
            d = self._levenshtein_distance(normalizado, c)
            if d < menor_dist:
                menor_dist = d
                melhor = c

        if melhor and menor_dist <= 2:
            # Barreira extra: evitar sugestões "distantes" (ruído).
            ratio = difflib.SequenceMatcher(None, normalizado, melhor).ratio()
            if ratio >= 0.75:
                return melhor
        return None

    def buscar_sugestoes(self, termo: str, palavras_banco: List[str] = None,
                         max_sugestoes: int = 5) -> List[Tuple[str, float]]:
        """Retorna múltiplas sugestões com scores."""
        banco = palavras_banco or list(self.palavras_banco)
        normalizado = self._normalizar(termo)
        matches = difflib.get_close_matches(normalizado, banco, n=max_sugestoes, cutoff=0.5)
        return [
            (m, round(difflib.SequenceMatcher(None, normalizado, m).ratio(), 3))
            for m in matches
        ]

    def _normalizar(self, texto: str) -> str:
        if not isinstance(texto, str):
            return ""
        texto = texto.lower().strip()
        texto = re.sub(r'[^\w\sáàâãéèêíìîóòôõúùûç]', '', texto)
        texto = re.sub(r'\s+', ' ', texto)
        return texto

    def _remover_acentos(self, texto: str) -> str:
        if not texto:
            return ""
        nfd = unicodedata.normalize('NFD', texto)
        return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')

    def _busca_difflib(self, termo: str, palavras: List[str], limite: float) -> Optional[str]:
        matches = difflib.get_close_matches(termo, palavras, n=1, cutoff=limite)
        if matches:
            return matches[0]
        if len(termo) >= 4:
            for p in self.termos_prioritarios:
                if p in palavras and difflib.SequenceMatcher(None, termo, p).ratio() >= limite:
                    return p
        return None

    def _levenshtein_correction(self, termo: str, palavras: List[str],
                                max_distance: int = 2) -> Optional[str]:
        melhor = None
        menor = max_distance + 1
        candidatos = [p for p in palavras if abs(len(p) - len(termo)) <= max_distance]
        for p in candidatos[:50]:
            d = self._levenshtein_distance(termo, p)
            if d < menor:
                menor = d
                melhor = p
                if d == 1:
                    break
        return melhor

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return CorretorOrtografico._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
            prev = curr
        return prev[-1]

    def _update_stats(self, tipo: str, start_time: float):
        self.stats["total_corrections"] += 1
        self.stats[tipo] += 1
        t = time.time() - start_time
        total = self.stats["total_corrections"]
        self.stats["avg_correction_time"] = (
            (self.stats["avg_correction_time"] * (total - 1) + t) / total
        )

    def get_stats(self) -> Dict:
        total = self.stats["total_corrections"]
        if total == 0:
            return self.stats
        return {
            **self.stats,
            "success_rate": round((total - self.stats["no_corrections"]) / total * 100, 2),
            "avg_correction_time_ms": round(self.stats["avg_correction_time"] * 1000, 2),
        }


# Instância global
corretor = CorretorOrtografico()
