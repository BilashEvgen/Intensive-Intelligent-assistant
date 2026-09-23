# Спільна логіка розпізнавання коротких голосових відповідей
# ("так"/"ні"/"стоп"/"додати .../видалити ...") - винесена окремо,
# щоб нею могли користуватись і app_confirm.py (перевірка слова по буквах),
# і delete_command.py (видалення команди), і будь-який інший майбутній сценарій,
# не дублюючи код.

from core.utils.fuzzy_match import find_best_keyword_match, similarity

# Для команд типу "додати команду"/"видалити команду" чи "додати літеру"/"видалити
# літеру" звичайного нечіткого пошуку по всій фразі недостатньо: у пари фраз є
# спільне слово ("команду"/"літеру"), тому вони плутаються одна з одною при
# порозі 0.75 (схожість такої пари фраз ~0.78-0.8). Тому порівнюємо лише
# дієслово-дію (перше слово) з вищим порогом.
ACTION_VERB_THRESHOLD = 0.8


def normalize_words(text: str):
    return [w.strip(",.!?") for w in text.lower().split()]


def matches_action(text: str, keyword_variants: list) -> bool:
    """Перевіряє, чи містить text дієслово-дію з keyword_variants (порівнюючи
    лише перше слово кожного варіанту, а не всю фразу - див. коментар вище)."""
    if not text:
        return False

    text_words = normalize_words(text)

    for variant in keyword_variants:
        verb = variant.lower().split()[0]
        if any(similarity(verb, w) >= ACTION_VERB_THRESHOLD for w in text_words):
            return True

    return False


def has_negation(text: str) -> bool:
    """
    Дуже надійна ознака заперечення: окреме слово "не"/"ні", або слово,
    що починається з префікса "не" ("неправильно", "невірно", "нема" ...).
    Треба перевіряти це ДО порівняння з confirm-словами, бо інакше "не так"
    (заперечення) хибно розпізнається як підтвердження лише тому, що містить
    підрядок "так" (звичайний пошук підрядка: "так" in "не так" -> True),
    так само як "неправильно" містить підрядок "правильно".
    """
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
    """
    Перевіряє, чи відповідь означає "залиш" - користувач хоче залишити
    початково почуте слово (heard_word) без змін, ігноруючи запропоновані
    словником варіанти.
    """
    if not text:
        return False
    return find_best_keyword_match(commands.get("keep", []), text)


def is_deny(text, commands: dict) -> bool:
    """
    Перевіряє, чи відповідь означає "не підходить" (варіант невірний, потрібен
    інший) - на відміну від is_cancel ("стоп", повністю скасувати дію).
    """
    if not text:
        return False
    if find_best_keyword_match(commands.get("deny", []), text):
        return True
    # "не так", "не воно" і подібні конструкції з запереченням теж рахуємо
    # як "не підходить", якщо це не команда скасування
    return has_negation(text) and not is_cancel(text, commands)
