"""Small, dependency-free text helpers tuned for Spanish and English policy text."""

from __future__ import annotations

import re
import unicodedata

_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)*")

STOPWORDS = frozenset(
    """
    a al ante con de del desde el en entre es la las lo los o para por que se sin su sus
    un una uno y e u ni no si mas muy cada todo toda todos todas este esta estos estas
    the of and or to in for on by with is are be at as an a from that this
    """.split()
)


def fold(text: str) -> str:
    """Lowercase and strip accents (ñ becomes n)."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def stem(token: str) -> str:
    """Very light Spanish/English suffix stripping: enough to match plurals."""
    for suffix in ("ciones", "cion", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)] + ("cion" if suffix.startswith("cion") else "")
    return token


def tokens(text: str, keep_stopwords: bool = False) -> list[str]:
    out = []
    for tok in _TOKEN.findall(fold(text)):
        if not keep_stopwords and tok in STOPWORDS:
            continue
        out.append(stem(tok))
    return out


def contains_phrase(haystack: list[str], phrase: list[str]) -> bool:
    if not phrase:
        return False
    n = len(phrase)
    first = phrase[0]
    for i, tok in enumerate(haystack):
        if tok == first and haystack[i : i + n] == phrase:
            return True
    return False


def squash(text: str) -> str:
    """Normalize whitespace and case for robust substring comparison of quotes."""
    return re.sub(r"\s+", " ", fold(text)).strip(" .\"'«»“”")
