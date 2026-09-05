"""Text helpers used by clustering, search and slugs."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")

# Words that carry no discriminating signal when comparing two civic reports.
STOPWORDS = frozenset(
    """
    a an the is are was were be been being of in on at to for with by from and or
    not no this that these those there here it its as very please kindly sir madam
    problem issue complaint report area near our my we us they them
    """.split()
)


def normalize(text: str) -> str:
    """Casefold, strip accents and punctuation, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _WORD_RE.sub(" ", text.casefold())
    return _WS_RE.sub(" ", text).strip()


def tokens(text: str) -> set[str]:
    return {word for word in normalize(text).split() if word and word not in STOPWORDS}


def jaccard(a: str, b: str) -> float:
    """Token overlap. Good at `broken road near X` vs `road broken at X`."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def sequence_ratio(a: str, b: str) -> float:
    """Character-level similarity. Catches typos that token overlap misses."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def similarity(a: str, b: str) -> float:
    """Blended score in [0, 1] used by duplicate detection.

    Token overlap is weighted higher because civic reports vary far more in
    phrasing than in vocabulary.
    """
    return round(0.65 * jaccard(a, b) + 0.35 * sequence_ratio(a, b), 4)


def truncate(text: str, limit: int = 160) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"
