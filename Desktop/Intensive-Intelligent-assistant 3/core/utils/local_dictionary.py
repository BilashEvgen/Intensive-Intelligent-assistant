# Локальний словник українських слів (частотний список, взятий з відкритого
# корпусу) + пошук найбільш схожих слів до заданого.
#
# На відміну від API словника (dictionary_api.py, LanguageTool), який
# підказує заміни ТІЛЬКИ для слів з орфографічною помилкою - цей пошук working
# незалежно від того, чи є вихідне слово "правильним". Це важливо, бо
# найчастіша причина "не той застосунок" - не помилка друку, а розпізнавач
# мовлення почув ІНШЕ РЕАЛЬНЕ слово ("рака" замість "рука"). LanguageTool в
# такому випадку промовчить (слово "рака" саме по собі правильне), а цей
# пошук - ні.

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
    """Завантажує список слів у пам'ять один раз (кешується на весь час роботи процесу)."""
    try:
        with open(WORDLIST_PATH, "r", encoding="utf-8") as f:
            return tuple(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return tuple()


def find_similar_words(word: str, limit: int = 15, min_similarity: float = DEFAULT_MIN_SIMILARITY) -> list:
    """
    Перебирає локальний словник і повертає до `limit` слів, найбільш схожих
    на `word` за написанням/звучанням, відсортованих за спаданням схожості.
    Слово, що збігається з самим `word`, у результат не потрапляє.
    """
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
