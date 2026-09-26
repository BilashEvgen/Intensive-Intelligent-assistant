import requests

from core.utils.local_dictionary import find_similar_words

LANGUAGETOOL_URL = "https://api.languagetool.org/v2/check"
LANGUAGETOOL_LANGUAGE = "uk-UA"
REQUEST_TIMEOUT = 5.0


def fetch_dictionary_suggestions(word: str, language: str = LANGUAGETOOL_LANGUAGE) -> list:
    """Повертає варіанти слова з LanguageTool."""
    word = (word or "").strip()
    if not word:
        return []

    try:
        response = requests.post(
            LANGUAGETOOL_URL,
            data={"text": word, "language": language},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    suggestions = []
    seen = set()

    for match in data.get("matches", []):
        for replacement in match.get("replacements", []):
            value = replacement.get("value", "").strip()
            key = value.lower()
            if value and key != word.lower() and key not in seen:
                seen.add(key)
                suggestions.append(value)

    return suggestions


def get_suggestions_for_word(word: str, language: str = LANGUAGETOOL_LANGUAGE, local_limit: int = 15) -> list:
    """Об'єднує локальні та API-варіанти слова."""
    word = (word or "").strip()
    if not word:
        return []

    local_matches = find_similar_words(word, limit=local_limit)
    api_matches = fetch_dictionary_suggestions(word, language=language)

    merged = []
    seen = {word.lower()}
    for candidate in local_matches + api_matches:
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            merged.append(candidate)

    return merged


def get_next_suggestions(all_suggestions: list, offset: int, limit: int = 3) -> tuple:
    """Повертає наступну порцію варіантів і нову позицію."""
    batch = all_suggestions[offset: offset + limit]
    return batch, offset + limit
