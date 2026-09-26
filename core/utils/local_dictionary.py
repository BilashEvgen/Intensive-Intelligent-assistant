import os
from functools import lru_cache

from core.utils.fuzzy_match import similarity

WORDLIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "uk_words.txt",
)

DEFAULT_MIN_SIMILARITY = 0.5


@lru_cache(maxsize=1)
def _load_wordlist() -> tuple:
    """Завантажує локальний список слів."""
    try:
        with open(WORDLIST_PATH, "r", encoding="utf-8") as f:
            return tuple(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return tuple()


def find_similar_words(word: str, limit: int = 15, min_similarity: float = DEFAULT_MIN_SIMILARITY) -> list:
    """Повертає найбільш схожі слова з локального словника."""
    word = (word or "").strip().lower()
    if not word:
        return []

    scored = []
    for candidate in _load_wordlist():
        if candidate == word:
            continue
        score = similarity(word, candidate)
        if score >= min_similarity:
            scored.append((candidate, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)

    return [w for w, _ in scored[:limit]]
