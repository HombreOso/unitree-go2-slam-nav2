"""
Retrieval over the OSHA corpus for layer B2.

Deliberately a lexical retriever (BM25 + a small domain-synonym expansion), not
an embedding model. Three reasons:

1. The corpus is ~30 chunks. Dense retrieval earns its keep at scale; here it
   would add a model dependency and an index to keep in sync for no measurable
   recall gain.
2. Safety regulation is unusually keyword-driven - "GFCI", "1926.501", "three
   points of contact" are exact terms, and lexical matching handles those
   better than embeddings, which tend to smear them together.
3. It is inspectable. The paper's whole argument is traceability, and here you
   can see precisely why a chunk was retrieved.

The synonym table is what bridges VLM vocabulary ("puddle", "orange vest") to
regulatory vocabulary ("wet location", "high-visibility apparel"), which is the
one place a purely lexical retriever would otherwise fall down.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from . import config

# VLM-vocabulary -> regulatory-vocabulary bridges. Each key, when seen in the
# query, adds its expansion terms.
SYNONYMS = {
    "puddle": ["wet", "water", "damp", "location", "gfci"],
    "water": ["wet", "damp", "gfci", "ground", "fault"],
    "wet": ["gfci", "ground", "fault", "damp"],
    "cord": ["flexible", "cable", "extension", "temporary", "wiring"],
    "cable": ["cord", "flexible", "wiring"],
    "extension": ["cord", "flexible", "temporary", "gfci"],
    "vest": ["high", "visibility", "warning", "garment", "conspicuous", "ppe"],
    "hivis": ["high", "visibility", "warning", "garment"],
    "helmet": ["hard", "hat", "head", "protection", "ppe"],
    "hardhat": ["hard", "hat", "head", "protection", "ppe"],
    "hat": ["hard", "head", "protection", "helmet", "ppe"],
    "ladder": ["portable", "rungs", "rails", "climbing", "1926.1053"],
    "climbing": ["ladder", "three", "points", "contact", "access"],
    "brick": ["material", "storage", "debris", "housekeeping", "stacked", "tier"],
    "bricks": ["material", "storage", "debris", "housekeeping", "stacked", "tier"],
    "debris": ["housekeeping", "scrap", "cleared", "passageway"],
    "clutter": ["housekeeping", "debris", "obstructed", "aisle"],
    "scattered": ["debris", "housekeeping", "cleared"],
    "walkway": ["aisle", "passageway", "egress", "clear"],
    "aisle": ["passageway", "walkway", "clear", "movement"],
    "forklift": ["powered", "industrial", "truck", "material", "handling",
                 "unattended", "load", "struck"],
    "forks": ["forklift", "load", "lowered", "unattended"],
    "pallet": ["material", "storage", "load", "stacked"],
    "lift": ["hoist", "material", "riders", "platform", "elevate"],
    "platform": ["scaffold", "guardrail", "elevated", "edge"],
    "roof": ["unprotected", "edge", "fall", "guardrail"],
    "edge": ["unprotected", "guardrail", "fall", "arrest"],
    "harness": ["fall", "arrest", "anchorage", "lanyard", "tie"],
    "machine": ["equipment", "machinery", "unattended"],
    "crate": ["stacked", "improvised", "access", "step"],
    "sign": ["signage", "caution", "danger", "warning", "posted"],
    "worker": ["employee", "personnel"],
    "person": ["employee", "worker", "personnel"],
    "elevated": ["height", "fall", "above", "lower", "level"],
    "height": ["elevated", "fall", "above", "feet"],
    "unattended": ["unattended", "operator", "lowered", "neutralized"],
}

STOPWORDS = set("""
a an the and or of to in on at is are was were be been being with for from by
this that these those it its as into over under near not no non do does did
there here they them their he she his her you your we our i me my if then than
which who whom what when where how all any both each few more most other some
such only own same so too very can will just should now also very much
image photo picture scene shows showing appears visible seen see look looks
""".split())


def tokenize(text: str) -> list[str]:
    # Keep regulation numbers such as 1926.404(b) intact enough to match.
    text = text.lower()
    text = re.sub(r"[^\w\s.()/-]", " ", text)
    toks = []
    for raw in text.split():
        raw = raw.strip(".,;:!?")
        if not raw or raw in STOPWORDS or len(raw) < 2:
            continue
        toks.append(raw)
    return toks


@dataclass
class Chunk:
    id: str
    citation: str
    title: str
    text: str

    @property
    def header(self) -> str:
        return f"[{self.id}] {self.citation} - {self.title}"


class OshaRetriever:
    """BM25 over the OSHA corpus."""

    K1 = 1.4
    B = 0.72

    def __init__(self, corpus_path: Path | None = None):
        self.chunks = self._parse(corpus_path or config.RULES_FILE)
        self._docs = [tokenize(f"{c.title} {c.citation} {c.text}") for c in self.chunks]
        self._tf = [Counter(d) for d in self._docs]
        self._len = [len(d) for d in self._docs]
        self._avg_len = sum(self._len) / max(len(self._len), 1)

        df = Counter()
        for d in self._docs:
            for term in set(d):
                df[term] += 1
        n = len(self._docs)
        self._idf = {
            t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _parse(path: Path) -> list[Chunk]:
        text = Path(path).read_text(encoding="utf-8")
        pattern = re.compile(
            r"^##\s*\[(?P<id>[A-Z0-9-]+)\]\s*(?P<cit>.+?)\s+[-—]\s+(?P<title>.+?)\s*$",
            re.MULTILINE)
        matches = list(pattern.finditer(text))
        chunks = []
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            chunks.append(Chunk(id=m.group("id"), citation=m.group("cit").strip(),
                                title=m.group("title").strip(), text=body))
        if not chunks:
            raise ValueError(f"No rule chunks parsed from {path}")
        return chunks

    # ------------------------------------------------------------------
    def _expand(self, tokens: list[str]) -> list[str]:
        out = list(tokens)
        for t in tokens:
            out.extend(SYNONYMS.get(t, ()))
        return out

    def search(self, query: str, top_k: int = 6) -> list[tuple[Chunk, float]]:
        q = self._expand(tokenize(query))
        if not q:
            return []
        scores = []
        for i, tf in enumerate(self._tf):
            s = 0.0
            dl = self._len[i]
            for term in q:
                f = tf.get(term)
                if not f:
                    continue
                idf = self._idf.get(term, 0.0)
                denom = f + self.K1 * (1 - self.B + self.B * dl / self._avg_len)
                s += idf * (f * (self.K1 + 1)) / denom
            if s > 0:
                scores.append((self.chunks[i], s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def format_context(self, results: list[tuple[Chunk, float]]) -> str:
        if not results:
            return "(no matching regulation found)"
        parts = []
        for chunk, score in results:
            parts.append(f"### {chunk.header}\n(retrieval score {score:.2f})\n{chunk.text}")
        return "\n\n".join(parts)


if __name__ == "__main__":
    r = OshaRetriever()
    print(f"{len(r.chunks)} chunks loaded.\n")
    for q in ["a worker stands on a ladder with no hard hat, "
              "the ladder leans against a forklift",
              "an orange extension cord runs through a puddle of water",
              "bricks are stacked on raised forklift forks with no operator"]:
        print(f"QUERY: {q}")
        for c, s in r.search(q, 4):
            print(f"   {s:6.2f}  {c.header}")
        print()
