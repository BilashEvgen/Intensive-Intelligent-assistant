from difflib import SequenceMatcher

DEFAULT_THRESHOLD =  0.75


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def fuzzy_word_in_text(keyword: str, text: str, threshold: float = DEFAULT_THRESHOLD) -> bool:
    if not keyword or not text:
        return False

    keyword = keyword.lower().strip()
    text = text.lower().strip()

    if keyword in text:
        return True

    keyword_words = keyword.split()
    if len(keyword_words) > 1:
        text_words = text.split()
        max_gap = 2

        for start in range(len(text_words)):
            text_pos = start
            kw_index = 0

            while kw_index < len(keyword_words) and text_pos < len(text_words):
                found_at = None

                for offset in range(max_gap + 1):
                    pos = text_pos + offset
                    if pos >= len(text_words):
                        break
                    if similarity(keyword_words[kw_index], text_words[pos]) >= threshold:
                        found_at = pos
                        break

                if found_at is None:
                    break

                kw_index += 1
                text_pos = found_at + 1

            if kw_index == len(keyword_words):
                return True

        window = len(keyword_words)
        for i in range(len(text_words) - window + 1):
            phrase = " ".join(text_words[i:i + window])
            if similarity(keyword, phrase) >= threshold:
                return True

        return similarity(keyword, text) >= threshold

    for word in text.split():
        if similarity(keyword, word) >= threshold:
            return True

    return False


def find_best_keyword_match(variants: list, text: str, threshold: float = DEFAULT_THRESHOLD) -> bool:

    for variant in variants:
        if fuzzy_word_in_text(variant, text, threshold):
            return True
    return False


def extract_app_name(command_text: str, keyword_variants: list, threshold: float = DEFAULT_THRESHOLD) -> str:
    """Видаляє ключові слова команди та повертає назву застосунку."""
    keyword_words = set()
    for variant in keyword_variants:
        for word in variant.lower().split():
            keyword_words.add(word)

    remaining = []
    for word in command_text.split():
        w = word.lower()
        is_keyword = w in keyword_words or any(
            similarity(w, kw) >= threshold for kw in keyword_words
        )
        if not is_keyword:
            remaining.append(word)

    return " ".join(remaining).strip()
