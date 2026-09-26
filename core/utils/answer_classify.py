from core.utils.fuzzy_match import find_best_keyword_match, similarity

ACTION_VERB_THRESHOLD = 0.8


def normalize_words(text: str):
    return [w.strip(",.!?") for w in text.lower().split()]


def matches_action(text: str, keyword_variants: list) -> bool:
    """Перевіряє дієслово дії у відповіді."""
    if not text:
        return False

    text_words = normalize_words(text)

    for variant in keyword_variants:
        verb = variant.lower().split()[0]
        if any(similarity(verb, w) >= ACTION_VERB_THRESHOLD for w in text_words):
            return True

    return False


def has_negation(text: str) -> bool:
    """Перевіряє наявність заперечення у відповіді."""
    for w in normalize_words(text):
        if w in ("не", "ні"):
            return True
        if w.startswith("не") and len(w) > 3:
            return True
    return False


def is_cancel(text, commands: dict) -> bool:
    if not text:
        return False
    return find_best_keyword_match(commands.get("cancel", []), text)


def is_confirm(text, commands: dict) -> bool:
    if not text or has_negation(text):
        return False
    return find_best_keyword_match(commands.get("confirm", []), text)


def is_keep(text, commands: dict) -> bool:
    """Перевіряє команду залишити почуте слово без змін."""
    if not text:
        return False
    return find_best_keyword_match(commands.get("keep", []), text)


def is_deny(text, commands: dict) -> bool:
    """Перевіряє відмову від поточного варіанта."""
    if not text:
        return False
    if find_best_keyword_match(commands.get("deny", []), text):
        return True
    return has_negation(text) and not is_cancel(text, commands)
