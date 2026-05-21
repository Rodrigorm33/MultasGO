"""
In-memory search index for MultasGO.

Goal: Google-like free-text search with ranking and typo tolerance,
without depending on dynamic SQL WHERE building.

The database is small (hundreds of rows), so we can safely keep an index
in memory and score matches per request.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.search.dictionaries.terms import BUSCAS_ESPECIAIS, CORRECOES, SINONIMOS
from app.search.normalizer import normalizar, normalizar_para_busca
from app.search.spell import corretor


# Minimal stopwords list for Portuguese search. Keep it small and domain-aware.
STOPWORDS: Set[str] = {
    "a",
    "o",
    "e",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "ao",
    "aos",
    "as",
    "os",
    "por",
    "para",
    "pra",
    "pro",
    "com",
    "sem",
    "sob",
    "sobre",
    "entre",
    "ate",
    "ate",
    "que",
    "se",
    "um",
    "uma",
    "uns",
    "umas",
    "nao",
    "não",
}


def _tokenize(norm: str) -> List[str]:
    # `normalizar()` already lowercases, removes accents/specials and collapses spaces.
    if not norm:
        return []
    return [t for t in norm.split() if t]


def _is_digits(token: str) -> bool:
    return token.isdigit()


def _severity_rank(gravidade_norm: str) -> int:
    g = (gravidade_norm or "").lower()
    if "gravissima" in g:
        return 1
    if "grave" in g:
        return 2
    if "media" in g:
        return 3
    if "leve" in g or "nao ha" in g:
        return 4
    return 5


@dataclass(frozen=True)
class IndexedDoc:
    codigo: str
    descricao: str
    responsavel: str
    valor_multa: float
    orgao_autuador: str
    artigos_ctb: str
    pontos: int
    gravidade: str

    # Normalized fields for scoring
    codigo_norm: str
    descricao_norm: str
    responsavel_norm: str
    orgao_norm: str
    artigos_norm: str
    gravidade_norm: str

    # Token sets for fast membership tests
    tokens_descricao: frozenset[str]
    tokens_orgao: frozenset[str]
    tokens_artigos: frozenset[str]
    tokens_responsavel: frozenset[str]
    tokens_gravidade: frozenset[str]
    tokens_all: frozenset[str]


@dataclass(frozen=True)
class Lexicon:
    vocab: frozenset[str]
    df: Dict[str, int]
    idf: Dict[str, float]
    top_terms: Tuple[Tuple[str, int], ...]
    top_phrases: Tuple[Tuple[str, int], ...]


class InMemorySearchIndex:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._built_at = 0.0
        self._docs: List[IndexedDoc] = []
        self._lexicon: Optional[Lexicon] = None

        # Pre-normalize synonym keys for phrase detection / token expansion.
        self._syn_map = {normalizar(k): v for k, v in SINONIMOS.items()}
        self._syn_phrase_keys = [k for k in self._syn_map.keys() if " " in k]

    @property
    def docs(self) -> List[IndexedDoc]:
        return self._docs

    @property
    def lexicon(self) -> Lexicon:
        if self._lexicon is None:
            # Should never happen after build, but keep defensive.
            return Lexicon(frozenset(), {}, {}, tuple(), tuple())
        return self._lexicon

    def invalidate(self) -> None:
        with self._lock:
            self._docs = []
            self._lexicon = None
            self._built_at = 0.0

    def build(self, db: Session) -> None:
        with self._lock:
            t0 = time.time()
            rows = db.execute(
                text(
                    """
                    SELECT
                        "Código de Infração" as codigo,
                        "Infração" as descricao,
                        "Responsável" as responsavel,
                        "Valor da multa" as valor_multa,
                        "Órgão Autuador" as orgao_autuador,
                        "Artigos do CTB" as artigos_ctb,
                        "Pontos" as pontos,
                        "Gravidade" as gravidade
                    FROM bdbautos
                    """
                )
            ).fetchall()

            docs: List[IndexedDoc] = []
            df: Dict[str, int] = {}
            tf: Dict[str, int] = {}
            phrase_counts: Dict[str, int] = {}

            def add_df(token_set: Iterable[str]) -> None:
                for tok in token_set:
                    df[tok] = df.get(tok, 0) + 1

            for r in rows:
                codigo = str(r.codigo) if r.codigo is not None else ""
                descricao = str(r.descricao) if r.descricao is not None else ""
                responsavel = str(r.responsavel) if r.responsavel is not None else ""
                orgao = str(r.orgao_autuador) if r.orgao_autuador is not None else ""
                artigos = str(r.artigos_ctb) if r.artigos_ctb is not None else ""
                gravidade = str(r.gravidade) if r.gravidade is not None else ""

                try:
                    valor_multa = float(r.valor_multa) if r.valor_multa else 0.0
                except (TypeError, ValueError):
                    valor_multa = 0.0
                try:
                    pontos = int(float(r.pontos)) if r.pontos else 0
                except (TypeError, ValueError):
                    pontos = 0

                codigo_norm = normalizar_para_busca(codigo)
                desc_norm = normalizar(descricao)
                resp_norm = normalizar(responsavel)
                orgao_norm = normalizar(orgao)
                artigos_norm = normalizar(artigos)
                grav_norm = normalizar(gravidade)

                toks_desc = [t for t in _tokenize(desc_norm) if t not in STOPWORDS]
                toks_orgao = [t for t in _tokenize(orgao_norm) if t not in STOPWORDS]
                toks_artigos = [t for t in _tokenize(artigos_norm) if t not in STOPWORDS]
                toks_resp = [t for t in _tokenize(resp_norm) if t not in STOPWORDS]
                toks_grav = [t for t in _tokenize(grav_norm) if t not in STOPWORDS]
                toks_code = [t for t in _tokenize(normalizar(codigo)) if t]

                # Term frequencies (for "top terms")
                for tok in toks_desc + toks_orgao + toks_artigos + toks_resp + toks_grav:
                    if len(tok) >= 3:
                        tf[tok] = tf.get(tok, 0) + 1

                # Frequent phrases from description (bigrams/trigrams) to improve ranking.
                for i in range(len(toks_desc) - 1):
                    ph = f"{toks_desc[i]} {toks_desc[i + 1]}"
                    phrase_counts[ph] = phrase_counts.get(ph, 0) + 1
                for i in range(len(toks_desc) - 2):
                    ph = f"{toks_desc[i]} {toks_desc[i + 1]} {toks_desc[i + 2]}"
                    phrase_counts[ph] = phrase_counts.get(ph, 0) + 1

                set_desc = frozenset(toks_desc)
                set_orgao = frozenset(toks_orgao)
                set_artigos = frozenset(toks_artigos)
                set_resp = frozenset(toks_resp)
                set_grav = frozenset(toks_grav)
                set_all = frozenset(set_desc | set_orgao | set_artigos | set_resp | set_grav | frozenset(toks_code))

                add_df(set_all)

                docs.append(
                    IndexedDoc(
                        codigo=codigo,
                        descricao=descricao,
                        responsavel=responsavel,
                        valor_multa=valor_multa,
                        orgao_autuador=orgao,
                        artigos_ctb=artigos,
                        pontos=pontos,
                        gravidade=gravidade,
                        codigo_norm=codigo_norm,
                        descricao_norm=desc_norm,
                        responsavel_norm=resp_norm,
                        orgao_norm=orgao_norm,
                        artigos_norm=artigos_norm,
                        gravidade_norm=grav_norm,
                        tokens_descricao=set_desc,
                        tokens_orgao=set_orgao,
                        tokens_artigos=set_artigos,
                        tokens_responsavel=set_resp,
                        tokens_gravidade=set_grav,
                        tokens_all=set_all,
                    )
                )

            n = max(len(docs), 1)
            idf = {t: (math.log((n + 1) / (df_t + 1)) + 1.0) for t, df_t in df.items()}
            vocab = frozenset(df.keys())

            top_terms = tuple(sorted(tf.items(), key=lambda x: x[1], reverse=True)[:200])
            top_phrases = tuple(sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)[:200])

            self._docs = docs
            self._lexicon = Lexicon(vocab=vocab, df=df, idf=idf, top_terms=top_terms, top_phrases=top_phrases)
            self._built_at = time.time()

            # Update global spell corrector vocabulary with DB terms.
            try:
                corretor.atualizar_vocabulario(set(vocab))
            except Exception:
                pass

            logger.info(f"[SEARCH] In-memory index built: {len(docs)} docs, {len(vocab)} tokens in {int((time.time()-t0)*1000)}ms")

    def _expand_query(self, query_original: str) -> Tuple[str, List[str], List[str], List[str]]:
        """
        Returns:
            (query_norm_full, tokens, tokens_no_stop, expansions)
        """
        query_norm_full = normalizar(query_original)
        tokens = _tokenize(query_norm_full)
        tokens_no_stop = [t for t in tokens if t not in STOPWORDS]

        # Apply direct dictionary corrections token-by-token.
        corrected = [CORRECOES.get(t, t) for t in tokens_no_stop]

        expansions: List[str] = list(corrected)

        # Spell suggestions as expansions (typo tolerance).
        # This is safe because we only expand using the DB vocabulary.
        vocab = self.lexicon.vocab
        for tok in corrected:
            if not tok or tok in STOPWORDS:
                continue
            if _is_digits(tok):
                continue
            if tok in vocab:
                continue
            if len(tok) < 3:
                continue
            try:
                sug = corretor.sugerir(tok)
            except Exception:
                sug = None
            if sug:
                expansions.append(str(sug))

            # Simple plural fallback (avoids needing an explicit synonyms list for plurals).
            if tok.endswith("s") and len(tok) >= 5:
                expansions.append(tok[:-1])

        # Phrase synonyms (e.g., "furar sinal" -> special trigger).
        padded = f" {query_norm_full} "
        for phrase in self._syn_phrase_keys:
            if f" {phrase} " in padded:
                expansions.extend(self._syn_map.get(phrase, []))

        # Token synonyms
        for tok in corrected:
            expansions.extend(self._syn_map.get(tok, []))

        # Normalize expansions and map special triggers to codes.
        out: List[str] = []
        for ex in expansions:
            if not ex:
                continue
            if ex.endswith("_especial") and ex in BUSCAS_ESPECIAIS:
                out.extend(BUSCAS_ESPECIAIS.get(ex, []))
                continue
            out.append(normalizar(ex))

        # Deduplicate preserving order.
        seen = set()
        uniq: List[str] = []
        for t in out:
            if t and t not in seen:
                seen.add(t)
                uniq.append(t)

        return query_norm_full, tokens, tokens_no_stop, uniq

    def _score_doc(
        self,
        doc: IndexedDoc,
        query_norm_full: str,
        q_tokens: Sequence[str],
        q_expanded: Sequence[str],
        *,
        allow_expanded_without_match: bool,
    ) -> float:
        idf = self.lexicon.idf

        # Field weights: description dominates, then articles, then orgao/responsavel.
        W_DESC = 4.0
        W_ART = 2.0
        W_ORGAO = 1.5
        W_RESP = 1.0
        W_GRAV = 0.5

        score = 0.0

        # Full phrase boost when the normalized query appears in the description.
        if len(query_norm_full) >= 4 and query_norm_full in doc.descricao_norm:
            score += 8.0

        matched = 0
        for tok in q_tokens:
            if not tok or tok in STOPWORDS:
                continue

            tok_idf = idf.get(tok, 1.0)

            if _is_digits(tok):
                # Codes: strong signal.
                if tok == doc.codigo_norm.replace("-", "").replace(" ", ""):
                    score += 30.0
                    matched += 1
                    continue
                if tok in doc.codigo_norm:
                    score += 15.0
                    matched += 1
                if tok in doc.artigos_norm:
                    score += 6.0
                    matched += 1
                continue

            if tok in doc.tokens_descricao:
                score += tok_idf * W_DESC
                matched += 1
            elif tok in doc.tokens_artigos:
                score += tok_idf * W_ART
                matched += 1
            elif tok in doc.tokens_orgao:
                score += tok_idf * W_ORGAO
                matched += 1
            elif tok in doc.tokens_responsavel:
                score += tok_idf * W_RESP
                matched += 1
            elif tok in doc.tokens_gravidade:
                score += tok_idf * W_GRAV
                matched += 1
            elif len(tok) >= 3:
                # Prefix/substring tolerance (Google-like): boosts without requiring an exact token.
                # Use small weights to avoid noise.
                if any(t.startswith(tok) for t in doc.tokens_descricao):
                    score += tok_idf * 1.2
                    matched += 1
                elif any(t.startswith(tok) for t in doc.tokens_artigos):
                    score += tok_idf * 0.8
                    matched += 1
                elif any(t.startswith(tok) for t in doc.tokens_orgao):
                    score += tok_idf * 0.6
                    matched += 1

        # Expanded terms contribute with smaller weight.
        for tok in q_expanded:
            if not tok or tok in STOPWORDS:
                continue
            if tok in q_tokens:
                continue
            tok_idf = idf.get(tok, 1.0)
            if not allow_expanded_without_match and matched == 0 and not _is_digits(tok):
                continue

            if _is_digits(tok):
                # Special triggers can expand to specific codes; treat that as a strong signal.
                code_digits = doc.codigo_norm.replace("-", "").replace(" ", "")
                if tok == code_digits:
                    score += 20.0
                    continue
                if tok in code_digits:
                    score += 10.0
                if tok in doc.artigos_norm:
                    score += 4.0
                continue

            if tok in doc.tokens_all:
                # Keep it small to avoid noise; expansions are "soft".
                score += tok_idf * 0.35

        # Prefer docs that match more query tokens (Google-like).
        score += matched * 1.2

        return score

    def search(self, query_original: str, *, limit: int, skip: int) -> Tuple[List[IndexedDoc], int, Optional[str]]:
        query_norm_full, tokens, tokens_no_stop, expanded = self._expand_query(query_original)

        q_tokens = [t for t in tokens_no_stop if len(t) >= 2]
        q_expanded = [t for t in expanded if len(t) >= 2]

        def _score_all(*, allow_expanded_without_match: bool) -> List[Tuple[float, int]]:
            out: List[Tuple[float, int]] = []
            for i, doc in enumerate(self._docs):
                s = self._score_doc(
                    doc,
                    query_norm_full,
                    q_tokens,
                    q_expanded,
                    allow_expanded_without_match=allow_expanded_without_match,
                )
                if s > 0:
                    out.append((s, i))
            return out

        # Pass 1: prefer matches on the user's tokens; expansions only help if there's at least 1 match.
        scored = _score_all(allow_expanded_without_match=False)

        # Pass 2 (fallback): if nothing matched, allow expansions (synonyms/corrections) to retrieve results.
        if not scored:
            scored = _score_all(allow_expanded_without_match=True)

        # If nothing matched, try per-token typo correction and suggest a better query.
        sugestao: Optional[str] = None
        if not scored and q_tokens:
            suggestion_tokens: List[str] = []
            changed = False
            vocab = self.lexicon.vocab
            for tok in q_tokens:
                if _is_digits(tok) or tok in vocab:
                    suggestion_tokens.append(tok)
                    continue
                sug = corretor.sugerir(tok)
                if sug and sug != tok:
                    suggestion_tokens.append(normalizar(sug))
                    changed = True
                else:
                    suggestion_tokens.append(tok)
            if changed:
                sugestao = " ".join(suggestion_tokens).strip() or None

        # Sort: score desc, severity, points desc, code.
        scored.sort(
            key=lambda x: (
                -x[0],
                _severity_rank(self._docs[x[1]].gravidade_norm),
                -self._docs[x[1]].pontos,
                self._docs[x[1]].codigo,
            )
        )

        total = len(scored)
        page = scored[skip : skip + limit]
        docs_page = [self._docs[i] for _, i in page]
        return docs_page, total, sugestao


_INDEX_LOCK = threading.RLock()
_INDEX: Optional[InMemorySearchIndex] = None


def get_index(db: Session) -> InMemorySearchIndex:
    global _INDEX
    with _INDEX_LOCK:
        if _INDEX is None:
            _INDEX = InMemorySearchIndex()
            _INDEX.build(db)
        elif not _INDEX.docs:
            _INDEX.build(db)
        return _INDEX


def invalidate_index() -> None:
    global _INDEX
    with _INDEX_LOCK:
        if _INDEX is not None:
            _INDEX.invalidate()
