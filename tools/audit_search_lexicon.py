"""
Audit the DB lexicon and compare with the manual dictionaries.

This script prints:
- DB token vocabulary and top terms
- frequent phrases (bigrams/trigrams) from descriptions
- coverage of TERMOS_PRIORITARIOS / SINONIMOS / CORRECOES against DB vocab

Run:
  python tools/audit_search_lexicon.py
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path
import sys
from typing import Iterable, List, Set, Tuple

from unidecode import unidecode

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.search.normalizer import normalizar
from app.search.dictionaries.terms import CORRECOES, SINONIMOS, TERMOS_PRIORITARIOS


DB_PATH = Path("multasgo.db")


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
    "que",
    "se",
    "um",
    "uma",
    "uns",
    "umas",
    "nao",
    "não",
}


def tokenize(text: str) -> List[str]:
    norm = normalizar(text)
    toks = [t for t in norm.split() if t]
    return toks


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    con = sqlite3.connect(str(DB_PATH))
    rows = con.execute(
        """
        SELECT
            [Código de infração],
            [Infração],
            [Responsável],
            [Órgão Autuador],
            [Artigos do CTB],
            [Gravidade]
        FROM bdbautos
        """
    ).fetchall()
    con.close()

    tf = Counter()
    vocab = set()
    bigrams = Counter()
    trigrams = Counter()

    for (_, desc, resp, orgao, art, grav) in rows:
        parts = [desc or "", resp or "", orgao or "", art or "", grav or ""]
        all_toks = []
        for p in parts:
            all_toks.extend(tokenize(p))

        toks = [t for t in all_toks if len(t) >= 3 and t not in STOPWORDS]
        tf.update(toks)
        vocab.update(toks)

        # Phrases only from description (better signal)
        desc_toks = [t for t in tokenize(desc or "") if len(t) >= 3 and t not in STOPWORDS]
        for i in range(len(desc_toks) - 1):
            bigrams[(desc_toks[i], desc_toks[i + 1])] += 1
        for i in range(len(desc_toks) - 2):
            trigrams[(desc_toks[i], desc_toks[i + 1], desc_toks[i + 2])] += 1

    print("Rows:", len(rows))
    print("Unique tokens (>=3, no stopwords):", len(vocab))

    print("\nTop tokens:")
    for tok, c in tf.most_common(60):
        print(f"{tok:22s} {c}")

    print("\nTop bigrams (desc):")
    for (a, b), c in bigrams.most_common(40):
        print(f"{a} {b:22s} {c}")

    print("\nTop trigrams (desc):")
    for (a, b, c3), c in trigrams.most_common(30):
        print(f"{a} {b} {c3:22s} {c}")

    prior = {unidecode(t.lower().strip()) for t in TERMOS_PRIORITARIOS}
    missing_prior = sorted([t for t in prior if t not in vocab])
    print("\nTERMOS_PRIORITARIOS:", len(prior))
    print("Covered in DB vocab:", len(prior) - len(missing_prior))
    print("Missing in DB vocab (first 50):", missing_prior[:50])

    # Synonyms coverage
    syn_keys = {unidecode(k.lower().strip()) for k in SINONIMOS.keys()}
    syn_vals = set()
    for vs in SINONIMOS.values():
        for v in vs:
            syn_vals.add(unidecode(str(v).lower().strip()))
    missing_syn_keys = sorted([k for k in syn_keys if k and k not in vocab and " " not in k])
    missing_syn_vals = sorted([v for v in syn_vals if v and v not in vocab and " " not in v and not v.endswith("_especial")])
    print("\nSINONIMOS keys:", len(syn_keys), "values:", len(syn_vals))
    print("Missing synonym keys in DB (first 50):", missing_syn_keys[:50])
    print("Missing synonym values in DB (first 50):", missing_syn_vals[:50])

    # Corrections coverage
    corr_values = {unidecode(v.lower().strip()) for v in CORRECOES.values()}
    missing_corr_values = sorted([v for v in corr_values if v and v not in vocab])
    print("\nCORRECOES values:", len(corr_values))
    print("Missing correction targets in DB (first 50):", missing_corr_values[:50])

    # Candidate additions for TERMOS_PRIORITARIOS
    top_not_in_prior = [t for (t, _) in tf.most_common(120) if t not in prior]
    print("\nCandidate tokens to add to TERMOS_PRIORITARIOS (first 60):")
    print(top_not_in_prior[:60])

    # Candidate frequent phrases to consider as special phrases / synonyms
    cand_phrases: List[Tuple[str, int]] = []
    for (a, b), c in bigrams.items():
        if c >= 4:
            cand_phrases.append((f"{a} {b}", c))
    for (a, b, c3), c in trigrams.items():
        if c >= 3:
            cand_phrases.append((f"{a} {b} {c3}", c))
    cand_phrases.sort(key=lambda x: x[1], reverse=True)
    print("\nCandidate frequent phrases (first 60):")
    for ph, c in cand_phrases[:60]:
        print(f"{ph:40s} {c}")


if __name__ == "__main__":
    main()
