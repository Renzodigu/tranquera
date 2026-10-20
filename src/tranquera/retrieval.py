"""Evidence retrieval: BM25 ranking plus explicit control tags from front matter."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from .ingest import Company
from .models import Chunk, Control
from .textutil import contains_phrase, tokens

TAG_BOOST = 6.0
PHRASE_BOOST = 2.0


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    phrase_match: bool  # chunk contains one of the control's keyword phrases
    tagged: bool        # the chunk's document lists the control in its front matter


class Retriever:
    def __init__(self, company: Company, k1: float = 1.4, b: float = 0.75):
        self.company = company
        self.k1, self.b = k1, b
        self.toks = {c.id: tokens(f"{c.heading}\n{c.text}") for c in company.chunks}
        self.tf = {cid: Counter(t) for cid, t in self.toks.items()}
        n = len(company.chunks) or 1
        self.avgdl = sum(len(t) for t in self.toks.values()) / n
        df: Counter = Counter()
        for t in self.toks.values():
            df.update(set(t))
        self.idf = {term: math.log(1 + (n - f + 0.5) / (f + 0.5)) for term, f in df.items()}
        self.doc_tags = {d.id: set(d.controls) for d in company.documents}

    def _bm25(self, chunk_id: str, query: list[str]) -> float:
        tf, dl = self.tf[chunk_id], len(self.toks[chunk_id])
        score = 0.0
        for term in set(query):
            f = tf.get(term)
            if not f:
                continue
            score += self.idf[term] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return score

    def search(self, control: Control, k: int = 8) -> list[Hit]:
        phrases = [tokens(kw) for kw in control.keywords]
        query = [t for p in phrases for t in p] + tokens(control.title_es) + tokens(control.title_en)
        hits = []
        for chunk in self.company.chunks:
            base = self._bm25(chunk.id, query)
            phrase = any(contains_phrase(self.toks[chunk.id], p) for p in phrases if p)
            tagged = control.id in self.doc_tags.get(chunk.doc_id, ())
            if not (base > 0 or tagged):
                continue
            score = base + (PHRASE_BOOST if phrase else 0) + (TAG_BOOST if tagged and base > 0 else 0)
            # A tagged document with no lexical overlap still surfaces, but ranks low.
            if tagged and base == 0:
                score = 0.5
            hits.append(Hit(chunk, round(score, 3), phrase, tagged))
        hits.sort(key=lambda h: (-h.score, h.chunk.id))
        return hits[:k]
